# core/realtime/neural_signal_processor.py

import asyncio
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
from scipy.signal import butter, filtfilt
import tensorflow as tf
from typing import List, Dict, Any
import time
import logging

class NeuralSignalProcessor:
    """High-performance real-time neural signal processing engine"""
    
    def __init__(self, sampling_rate: int = 1000, channels: int = 64):
        """
        Initialize NeuralSignalProcessor with desired sampling rate and number of channels.

        Parameters
        ----------
        sampling_rate : int, optional
            Sampling rate of the neural signal (default: 1000 Hz).
        channels : int, optional
            Number of channels in the neural signal (default: 64).

        Notes
        -----
        The constructor initializes a Kafka consumer and producer for low-latency
        streaming of neural signals. The consumer is configured to minimize latency
        by setting `fetch_max_wait_ms` to 1ms and `enable_auto_commit` to False.
        The producer is configured to use LZ4 compression and minimal batching delay
        of 1ms.
        """
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.buffer_size = 1000  # 1 second buffer
        self.signal_buffer = np.zeros((channels, self.buffer_size))
        self.model = self._load_model()
        
        # Kafka configuration for low-latency streaming
        self.consumer = KafkaConsumer(
            'neural_signals',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: np.frombuffer(m, dtype=np.float32),
            fetch_max_wait_ms=1,  # Minimize latency
            max_poll_records=1000,  # Batch processing
            enable_auto_commit=False
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda x: x.tobytes(),
            linger_ms=1,  # Minimal batching delay
            compression_type='lz4'
        )
        
        # Pre-computed filter coefficients for efficiency
        self.filter_coeffs = self._compute_filter_coefficients()
        
    def _load_model(self) -> tf.keras.Model:
        """Load pre-trained BCI classification model"""
        model = tf.keras.models.load_model('models/eeg_classifier.h5')
        # Optimize for inference
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy')
        return model
    
    def _compute_filter_coefficients(self) -> Dict[str, np.ndarray]:
        """Pre-compute filter coefficients for real-time filtering"""
        nyquist = self.sampling_rate / 2
        
        # Bandpass filter 1-40 Hz
        low_cutoff = 1.0 / nyquist
        high_cutoff = 40.0 / nyquist
        b, a = butter(4, [low_cutoff, high_cutoff], btype='band')
        
        # Notch filter for 50/60 Hz line noise
        notch_freq = 50.0 / nyquist
        notch_b, notch_a = butter(2, [notch_freq - 0.01, notch_freq + 0.01], btype='bandstop')
        
        return {
            'bandpass': (b, a),
            'notch': (notch_b, notch_a)
        }
    
    async def process_signal_stream(self):
        """Main processing loop for real-time signal processing"""
        processing_times = []
        
        while True:
            try:
                # Consume neural signal data
                msg_pack = self.consumer.poll(timeout_ms=1)
                
                for topic_partition, messages in msg_pack.items():
                    for message in messages:
                        start_time = time.time()
                        
                        # Deserialize neural data
                        signal_data = message.value.reshape(self.channels, -1)
                        
                        # Real-time filtering
                        filtered_signal = self._apply_filters(signal_data)
                        
                        # Update circular buffer
                        self._update_buffer(filtered_signal)
                        
                        # Feature extraction
                        features = self._extract_features()
                        
                        # Model inference
                        prediction = self.model.predict(features, verbose=0)
                        
                        # Prepare output
                        result = {
                            'timestamp': message.timestamp,
                            'prediction': prediction.tolist(),
                            'confidence': np.max(prediction),
                            'processing_time_ms': (time.time() - start_time) * 1000
                        }
                        
                        # Send processed results
                        await self._send_result(result)
                        
                        processing_times.append(result['processing_time_ms'])
                        
                        # Performance monitoring
                        if len(processing_times) % 1000 == 0:
                            avg_time = np.mean(processing_times[-1000:])
                            logging.info(f"Average processing time: {avg_time:.2f}ms")
                            
            except Exception as e:
                logging.error(f"Processing error: {e}")
                await asyncio.sleep(0.001)  # Brief pause before retry
    
    def _apply_filters(self, signal: np.ndarray) -> np.ndarray:
        """Apply real-time digital filters"""
        # Bandpass filter
        b, a = self.filter_coeffs['bandpass']
        filtered = filtfilt(b, a, signal, axis=1)
        
        # Notch filter
        b, a = self.filter_coeffs['notch']
        filtered = filtfilt(b, a, filtered, axis=1)
        
        return filtered
    
    def _update_buffer(self, signal: np.ndarray):
        """Update circular buffer with new signal data"""
        signal_len = signal.shape[1]
        self.signal_buffer = np.roll(self.signal_buffer, -signal_len, axis=1)
        self.signal_buffer[:, -signal_len:] = signal
    
    def _extract_features(self) -> np.ndarray:
        """Extract features for classification"""
        # Power spectral density features
        freqs = np.fft.fftfreq(self.buffer_size, 1/self.sampling_rate)
        psd = np.abs(np.fft.fft(self.signal_buffer, axis=1))**2
        
        # Extract band power features
        alpha_band = np.mean(psd[:, (freqs >= 8) & (freqs <= 12)], axis=1)
        beta_band = np.mean(psd[:, (freqs >= 13) & (freqs <= 30)], axis=1)
        gamma_band = np.mean(psd[:, (freqs >= 31) & (freqs <= 40)], axis=1)
        
        features = np.concatenate([alpha_band, beta_band, gamma_band])
        return features.reshape(1, -1)
    
    async def _send_result(self, result: Dict[str, Any]):
        """Send processed results to output topic"""
        self.producer.send('neural_results', value=result)
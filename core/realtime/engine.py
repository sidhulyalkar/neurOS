# neuros/core/realtime/engine.py
"""
Real-time Processing Engine for neurOS
Handles sub-100ms latency BCI processing with adaptive optimization
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from collections import deque
import threading
import queue

@dataclass
class RealtimeConfig:
    """Configuration for real-time processing"""
    target_latency_ms: float = 50.0
    max_buffer_size: int = 1000
    adaptive_optimization: bool = True
    thread_pool_size: int = 4
    enable_gpu_acceleration: bool = True
    monitoring_enabled: bool = True

@dataclass
class PerformanceMetrics:
    """Real-time performance tracking"""
    latency_ms: deque = field(default_factory=lambda: deque(maxlen=1000))
    throughput_samples_per_sec: deque = field(default_factory=lambda: deque(maxlen=100))
    dropped_samples: int = 0
    gpu_utilization: float = 0.0
    cpu_utilization: float = 0.0

class AdaptiveBuffer:
    """Self-tuning circular buffer for real-time data"""
    
    def __init__(self, initial_size: int = 100):
        self.buffer = np.zeros((initial_size, 64))  # Assume 64 channels max
        self.size = initial_size
        self.write_idx = 0
        self.read_idx = 0
        self.count = 0
        self.lock = threading.Lock()
        
    def put(self, data: np.ndarray) -> bool:
        """Add data to buffer, returns False if buffer full"""
        with self.lock:
            if self.count >= self.size:
                return False
            
            self.buffer[self.write_idx] = data
            self.write_idx = (self.write_idx + 1) % self.size
            self.count += 1
            return True
    
    def get(self, num_samples: int = 1) -> Optional[np.ndarray]:
        """Get samples from buffer"""
        with self.lock:
            if self.count < num_samples:
                return None
            
            if self.read_idx + num_samples <= self.size:
                data = self.buffer[self.read_idx:self.read_idx + num_samples].copy()
            else:
                # Wrap around
                first_part = self.buffer[self.read_idx:].copy()
                second_part = self.buffer[:num_samples - (self.size - self.read_idx)].copy()
                data = np.vstack([first_part, second_part])
            
            self.read_idx = (self.read_idx + num_samples) % self.size
            self.count -= num_samples
            return data
    
    def resize(self, new_size: int):
        """Dynamically resize buffer based on performance"""
        with self.lock:
            old_buffer = self.buffer
            self.buffer = np.zeros((new_size, old_buffer.shape[1]))
            
            # Copy existing data
            if self.count > 0:
                if self.read_idx < self.write_idx:
                    valid_data = old_buffer[self.read_idx:self.write_idx]
                else:
                    valid_data = np.vstack([
                        old_buffer[self.read_idx:],
                        old_buffer[:self.write_idx]
                    ])
                
                copy_size = min(valid_data.shape[0], new_size)
                self.buffer[:copy_size] = valid_data[:copy_size]
                self.count = copy_size
                self.read_idx = 0
                self.write_idx = copy_size % new_size
            
            self.size = new_size

class RealtimeProcessor:
    """High-performance real-time BCI processor"""
    
    def __init__(self, config: RealtimeConfig):
        self.config = config
        self.logger = logging.getLogger("neurOS.realtime")
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.is_running = False
        self.should_stop = False
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=config.thread_pool_size)
        self.input_queue = queue.Queue(maxsize=config.max_buffer_size)
        self.output_queue = queue.Queue(maxsize=config.max_buffer_size)
        
        # Adaptive components
        self.buffer = AdaptiveBuffer()
        self.processing_pipeline = []
        self.callbacks = []
        
        # Optimization state
        self.last_optimization = time.time()
        self.optimization_interval = 5.0  # seconds
        
    def add_processor(self, processor: Callable[[np.ndarray], np.ndarray], 
                     priority: int = 0):
        """Add processing function to pipeline"""
        self.processing_pipeline.append((priority, processor))
        self.processing_pipeline.sort(key=lambda x: x[0])
    
    def add_callback(self, callback: Callable[[np.ndarray, Dict[str, Any]], None]):
        """Add result callback"""
        self.callbacks.append(callback)
    
    async def process_sample(self, data: np.ndarray, 
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process single sample with latency tracking"""
        start_time = time.perf_counter()
        
        try:
            # Apply processing pipeline
            result = data.copy()
            for _, processor in self.processing_pipeline:
                result = processor(result)
            
            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.latency_ms.append(latency_ms)
            
            # Prepare output
            output = {
                'processed_data': result,
                'latency_ms': latency_ms,
                'timestamp': time.time(),
                'metadata': metadata or {}
            }
            
            # Trigger callbacks
            for callback in self.callbacks:
                try:
                    callback(result, output)
                except Exception as e:
                    self.logger.error(f"Callback error: {e}")
            
            return output
            
        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            return {
                'error': str(e),
                'latency_ms': (time.perf_counter() - start_time) * 1000,
                'timestamp': time.time()
            }
    
    def _processing_worker(self):
        """Worker thread for processing samples"""
        while not self.should_stop:
            try:
                # Get sample from input queue
                item = self.input_queue.get(timeout=0.1)
                if item is None:  # Shutdown signal
                    break
                
                data, metadata = item
                
                # Process asynchronously
                future = asyncio.run_coroutine_threadsafe(
                    self.process_sample(data, metadata),
                    self.loop
                )
                
                # Put result in output queue
                try:
                    result = future.result(timeout=self.config.target_latency_ms / 1000)
                    self.output_queue.put(result)
                except asyncio.TimeoutError:
                    self.metrics.dropped_samples += 1
                    self.logger.warning("Sample processing timeout")
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
    
    def _optimization_worker(self):
        """Background optimization worker"""
        while not self.should_stop:
            time.sleep(self.optimization_interval)
            
            if not self.config.adaptive_optimization:
                continue
            
            try:
                self._optimize_performance()
            except Exception as e:
                self.logger.error(f"Optimization error: {e}")
    
    def _optimize_performance(self):
        """Adaptive performance optimization"""
        if len(self.metrics.latency_ms) < 10:
            return
        
        avg_latency = np.mean(list(self.metrics.latency_ms)[-100:])
        target_latency = self.config.target_latency_ms
        
        self.logger.info(f"Avg latency: {avg_latency:.2f}ms, Target: {target_latency}ms")
        
        # Adjust buffer size based on latency
        if avg_latency > target_latency * 1.5:
            # Reduce buffer to decrease latency
            new_size = max(50, int(self.buffer.size * 0.8))
            self.buffer.resize(new_size)
            self.logger.info(f"Reduced buffer size to {new_size}")
            
        elif avg_latency < target_latency * 0.7:
            # Increase buffer for stability
            new_size = min(1000, int(self.buffer.size * 1.2))
            self.buffer.resize(new_size)
            self.logger.info(f"Increased buffer size to {new_size}")
    
    async def start(self):
        """Start real-time processing engine"""
        if self.is_running:
            return
        
        self.is_running = True
        self.should_stop = False
        self.loop = asyncio.get_event_loop()
        
        # Start worker threads
        self.processing_thread = threading.Thread(target=self._processing_worker)
        self.optimization_thread = threading.Thread(target=self._optimization_worker)
        
        self.processing_thread.start()
        self.optimization_thread.start()
        
        self.logger.info("Real-time processing engine started")
    
    async def stop(self):
        """Stop processing engine"""
        if not self.is_running:
            return
        
        self.should_stop = True
        
        # Signal shutdown
        self.input_queue.put(None)
        
        # Wait for threads
        self.processing_thread.join()
        self.optimization_thread.join()
        
        # Cleanup
        self.executor.shutdown(wait=True)
        self.is_running = False
        
        self.logger.info("Real-time processing engine stopped")
    
    def submit_sample(self, data: np.ndarray, metadata: Dict[str, Any] = None) -> bool:
        """Submit sample for processing"""
        try:
            self.input_queue.put((data, metadata), block=False)
            return True
        except queue.Full:
            self.metrics.dropped_samples += 1
            return False
    
    def get_result(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """Get processed result"""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.metrics.latency_ms:
            return {}
        
        recent_latencies = list(self.metrics.latency_ms)[-100:]
        
        return {
            'avg_latency_ms': np.mean(recent_latencies),
            'max_latency_ms': np.max(recent_latencies),
            'min_latency_ms': np.min(recent_latencies),
            'latency_std_ms': np.std(recent_latencies),
            'dropped_samples': self.metrics.dropped_samples,
            'queue_size': self.input_queue.qsize(),
            'buffer_utilization': self.buffer.count / self.buffer.size,
            'target_latency_ms': self.config.target_latency_ms
        }

# Example usage and testing
if __name__ == "__main__":
    async def test_realtime_engine():
        # Configure engine
        config = RealtimeConfig(
            target_latency_ms=25.0,
            adaptive_optimization=True
        )
        
        engine = RealtimeProcessor(config)
        
        # Add simple processing function
        def bandpass_filter(data):
            # Simulate bandpass filtering
            time.sleep(0.001)  # 1ms processing time
            return data * 0.95
        
        engine.add_processor(bandpass_filter)
        
        # Add callback
        def print_result(data, metadata):
            print(f"Processed sample: {data.shape}, Latency: {metadata['latency_ms']:.2f}ms")
        
        engine.add_callback(print_result)
        
        # Start engine
        await engine.start()
        
        # Simulate real-time data
        for i in range(100):
            sample = np.random.randn(64)  # 64-channel sample
            engine.submit_sample(sample)
            
            # Get result
            result = engine.get_result()
            if result:
                print(f"Sample {i}: {result['latency_ms']:.2f}ms")
            
            await asyncio.sleep(0.004)  # 250 Hz sampling rate
        
        # Print final metrics
        metrics = engine.get_metrics()
        print("\nFinal Metrics:")
        for key, value in metrics.items():
            print(f"{key}: {value}")
        
        await engine.stop()
    
    # Run test
    asyncio.run(test_realtime_engine())
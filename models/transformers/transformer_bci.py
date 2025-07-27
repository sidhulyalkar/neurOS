# models/transformers/transformer_bci.py
"""
Transformer-based BCI Models for neurOS
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TransformerConfig:
    """Configuration for transformer BCI models"""
    # Signal parameters
    n_channels: int = 64
    seq_length: int = 1000  # 4 seconds at 250Hz
    sampling_rate: int = 250
    
    # Model architecture
    d_model: int = 256
    n_heads: int = 8
    n_layers: int = 4
    dropout: float = 0.1
    
    # Task parameters
    n_classes: int = 2  # Binary classification
    task_type: str = "motor_imagery"  # "motor_imagery", "p300", "ssvep"
    
    # Training parameters
    batch_size: int = 32
    learning_rate: float = 0.001
    epochs: int = 100

class EEGNetTransformer(nn.Module):
    """
    Novel Hybrid CNN-Transformer for BCI
    Combines EEGNet-style convolution with transformer attention
    """
    
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.config = config
        
        # EEGNet-inspired CNN feature extraction
        self.temporal_conv = nn.Conv2d(1, 16, (1, 64), padding=(0, 32))
        self.spatial_conv = nn.Conv2d(16, 32, (config.n_channels, 1), bias=False)
        self.spatial_bn = nn.BatchNorm2d(32)
        self.elu = nn.ELU()
        
        # Depthwise separable convolution
        self.separable_conv = nn.Conv2d(32, 32, (1, 16), padding=(0, 8), groups=32)
        self.pointwise_conv = nn.Conv2d(32, 64, 1)
        self.sep_bn = nn.BatchNorm2d(64)
        
        # Average pooling and dropout
        self.avg_pool = nn.AvgPool2d((1, 4))
        self.dropout = nn.Dropout(config.dropout)
        
        # Calculate sequence length after convolutions
        self.seq_len_after_conv = (config.seq_length + 2*32 - 64) // 4 + 1
        
        # Projection to transformer dimension
        self.projection = nn.Linear(64, config.d_model)
        
        # Positional encoding
        self.pos_encoding = PositionalEncoding(config.d_model, max_len=self.seq_len_after_conv)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=config.d_model * 4,
            dropout=config.dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.n_layers)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(config.d_model, config.d_model // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model // 2, config.n_classes)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        Args:
            x: Input tensor of shape (batch_size, channels, time_points)
        Returns:
            logits: Classification logits of shape (batch_size, n_classes)
        """
        batch_size = x.size(0)
        
        # Add channel dimension for 2D conv: (batch, 1, channels, time)
        x = x.unsqueeze(1)
        
        # CNN feature extraction
        x = self.temporal_conv(x)  # (batch, 16, channels, time)
        x = self.spatial_conv(x)   # (batch, 32, 1, time)
        x = self.spatial_bn(x)
        x = self.elu(x)
        
        x = self.separable_conv(x) # (batch, 32, 1, time)
        x = self.pointwise_conv(x) # (batch, 64, 1, time)
        x = self.sep_bn(x)
        x = self.elu(x)
        
        x = self.avg_pool(x)       # (batch, 64, 1, time//4)
        x = self.dropout(x)
        
        # Reshape for transformer: (batch, seq_len, features)
        x = x.squeeze(2).transpose(1, 2)  # (batch, time//4, 64)
        
        # Project to transformer dimension
        x = self.projection(x)  # (batch, seq_len, d_model)
        
        # Add positional encoding
        x = self.pos_encoding(x)
        
        # Apply transformer
        x = self.transformer(x)  # (batch, seq_len, d_model)
        
        # Global average pooling across time
        x = x.mean(dim=1)  # (batch, d_model)
        
        # Classification
        logits = self.classifier(x)  # (batch, n_classes)
        
        return logits

class PositionalEncoding(nn.Module):
    """Positional encoding for transformer"""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                           (-np.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        
        self.register_buffer('pe', pe)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        seq_len = x.size(1)
        return x + self.pe[:seq_len, :].transpose(0, 1)

class CircularBuffer:
    """Circular buffer for real-time EEG processing"""
    
    def __init__(self, max_samples: int, n_channels: int):
        self.max_samples = max_samples
        self.n_channels = n_channels
        self.buffer = np.zeros((n_channels, max_samples))
        self.write_pos = 0
        self.filled = False
        
    def add_samples(self, samples: np.ndarray):
        """Add samples to buffer (n_channels, n_new_samples)"""
        n_new = samples.shape[1]
        
        if n_new >= self.max_samples:
            # New data is larger than buffer - just take the last part
            self.buffer = samples[:, -self.max_samples:]
            self.write_pos = 0
            self.filled = True
        else:
            # Add samples circularly
            end_pos = self.write_pos + n_new
            
            if end_pos <= self.max_samples:
                # No wrap-around
                self.buffer[:, self.write_pos:end_pos] = samples
            else:
                # Wrap-around
                split_point = self.max_samples - self.write_pos
                self.buffer[:, self.write_pos:] = samples[:, :split_point]
                self.buffer[:, :end_pos - self.max_samples] = samples[:, split_point:]
            
            self.write_pos = end_pos % self.max_samples
            if end_pos >= self.max_samples:
                self.filled = True
    
    def get_window(self) -> np.ndarray:
        """Get current window (n_channels, max_samples)"""
        if not self.filled:
            return self.buffer[:, :self.write_pos]
        
        # Return data in chronological order
        if self.write_pos == 0:
            return self.buffer.copy()
        else:
            return np.concatenate([
                self.buffer[:, self.write_pos:],
                self.buffer[:, :self.write_pos]
            ], axis=1)
    
    def is_full(self) -> bool:
        return self.filled
    
    def fill_level(self) -> float:
        if self.filled:
            return 1.0
        return self.write_pos / self.max_samples

class RealTimeBCIInference:
    """
    Real-time BCI inference engine
    Simplified version without neurOS dependencies
    """
    
    def __init__(self, model_path: str, config: TransformerConfig):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model
        self.model = EEGNetTransformer(config)
        try:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        except:
            # If no model file, use random weights for demo
            logger.warning("Could not load model, using random weights for demo")
        
        self.model.to(self.device)
        self.model.eval()
        
        # Circular buffer for real-time processing
        self.buffer = CircularBuffer(config.seq_length, config.n_channels)
        
        # Performance monitoring
        self.latencies = []
        self.predictions = []
        
    async def process_chunk(self, eeg_chunk: np.ndarray) -> Dict[str, Any]:
        """
        Process a chunk of EEG data in real-time - FIXED VERSION
        Args:
            eeg_chunk: EEG data chunk (n_channels, n_samples)
        Returns:
            Prediction results with timing information
        """
        import time
        start_time = time.time()
        
        # Add to buffer
        self.buffer.add_samples(eeg_chunk)
        
        # Check if we have enough data - FIX: Always return dict with 'status'
        if not self.buffer.is_full():
            return {
                "status": "buffering", 
                "buffer_fill": self.buffer.fill_level(),
                "prediction": None,
                "confidence": 0.0,
                "probabilities": [0.5, 0.5],
                "latency_ms": 0.0,
                "timestamp": time.time()
            }
        
        # Get windowed data
        data = self.buffer.get_window()  # (n_channels, seq_length)
        
        # Normalize (simple z-score)
        data = (data - data.mean(axis=1, keepdims=True)) / (data.std(axis=1, keepdims=True) + 1e-8)
        
        # Convert to tensor
        input_tensor = torch.from_numpy(data).float().unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            logits = self.model(input_tensor)
            probs = torch.softmax(logits, dim=1)
            prediction = torch.argmax(logits, dim=1).item()
            confidence = probs.max().item()
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        self.latencies.append(latency_ms)
        
        # Store prediction - FIX: Always include 'status'
        result = {
            "status": "ready",  # FIX: Always include status
            "prediction": prediction,
            "confidence": confidence,
            "probabilities": probs.cpu().numpy().tolist()[0],
            "latency_ms": latency_ms,
            "timestamp": time.time()
        }
        
        self.predictions.append(result)
        
        # Keep only recent predictions (last 100)
        if len(self.predictions) > 100:
            self.predictions = self.predictions[-100:]
            self.latencies = self.latencies[-100:]
        
        return result
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get real-time performance metrics"""
        if not self.latencies:
            return {
                "avg_latency_ms": 0, 
                "p95_latency_ms": 0, 
                "throughput_hz": 0,
                "total_predictions": 0  
            }
        
        return {
            "avg_latency_ms": np.mean(self.latencies),
            "p95_latency_ms": np.percentile(self.latencies, 95),
            "throughput_hz": 1000 / np.mean(self.latencies) if self.latencies else 0,
            "total_predictions": len(self.predictions)
        }
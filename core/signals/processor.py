# core/signals/processor.py
from typing import Protocol, Dict, Any
import numpy as np

class SignalProcessor(Protocol):
    """Protocol for signal processors"""
    
    def process(self, data: np.ndarray, metadata: SignalMetadata) -> tuple[np.ndarray, Dict[str, Any]]:
        """Process signal data"""
        ...

class ProcessingPipeline:
    """Composable signal processing pipeline"""
    
    def __init__(self):
        self._processors: list[SignalProcessor] = []
        
    def add(self, processor: SignalProcessor) -> 'ProcessingPipeline':
        """Add processor to pipeline"""
        self._processors.append(processor)
        return self
        
    def process(self, data: np.ndarray, metadata: SignalMetadata) -> tuple[np.ndarray, Dict[str, Any]]:
        """Run all processors in sequence"""
        all_metrics = {}
        
        for processor in self._processors:
            data, metrics = processor.process(data, metadata)
            all_metrics.update(metrics)
            
        return data, all_metrics
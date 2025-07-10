# core/realtime/adaptive_processor.py
import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from dataclasses import dataclass
from contextlib import contextmanager
import psutil
import GPUtil

@dataclass
class MetricsConfig:
    """Configuration for enterprise metrics collection"""
    enable_gpu_metrics: bool = True
    enable_system_metrics: bool = True
    collection_interval: float = 1.0
    export_port: int = 8080

class EnterpriseMetrics:
    """Comprehensive metrics collection for BCI enterprise systems"""
    
    def __init__(self, config: MetricsConfig):
        self.config = config
        self._setup_metrics()
        
    def _setup_metrics(self):
        """Initialize Prometheus metrics"""
        # Neural signal processing metrics
        self.neural_signals_processed = Counter(
            'neurOS_neural_signals_processed_total',
            'Total number of neural signals processed',
            ['device_id', 'channel_count', 'sampling_rate']
        )
        
        self.signal_processing_duration = Histogram(
            'neurOS_signal_processing_duration_seconds',
            'Time spent processing neural signals',
            ['processing_stage', 'device_type'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )
        
        self.model_inference_duration = Histogram(
            'neurOS_model_inference_duration_seconds',
            'Time spent on model inference',
            ['model_name', 'model_version'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
        )
        
        self.active_devices = Gauge(
            'neurOS_active_devices',
            'Number of active BCI devices',
            ['device_type', 'connection_status']
        )
        
        self.model_accuracy = Gauge(
            'neurOS_model_accuracy',
            'Current model accuracy score',
            ['model_name', 'dataset']
        )
        
        self.data_quality_score = Gauge(
            'neurOS_data_quality_score',
            'Neural signal quality score (0-1)',
            ['device_id', 'channel']
        )
        
        # System resource metrics
        self.cpu_usage = Gauge(
            'neurOS_cpu_usage_percent',
            'CPU usage percentage',
            ['core']
        )
        
        self.memory_usage = Gauge(
            'neurOS_memory_usage_bytes',
            'Memory usage in bytes',
            ['type']
        )
        
        self.gpu_utilization = Gauge(
            'neurOS_gpu_utilization_percent',
            'GPU utilization percentage',
            ['gpu_id', 'gpu_name']
        )
        
        self.gpu_memory_usage = Gauge(
            'neurOS_gpu_memory_usage_bytes',
            'GPU memory usage in bytes',
            ['gpu_id', 'type']
        )
        
        # Enterprise-specific metrics
        self.tenant_resource_usage = Gauge(
            'neurOS_tenant_resource_usage',
            'Resource usage per tenant',
            ['tenant_id', 'resource_type']
        )
        
        self.api_request_duration = Histogram(
            'neurOS_api_request_duration_seconds',
            'API request duration',
            ['endpoint', 'method', 'status_code'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        self.compliance_violations = Counter(
            'neurOS_compliance_violations_total',
            'Total compliance violations detected',
            ['violation_type', 'severity', 'tenant_id']
        )
        
        self.data_processing_lag = Gauge(
            'neurOS_data_processing_lag_seconds',
            'Current data processing lag',
            ['processing_stage', 'device_id']
        )
        
    @contextmanager
    def time_operation(self, metric_name: str, **labels):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            getattr(self, metric_name).labels(**labels).observe(duration)
    
    def record_signal_processing(self, device_id: str, channel_count: int, 
                               sampling_rate: int, processing_duration: float):
        """Record neural signal processing metrics"""
        self.neural_signals_processed.labels(
            device_id=device_id,
            channel_count=str(channel_count),
            sampling_rate=str(sampling_rate)
        ).inc()
        
        self.signal_processing_duration.labels(
            processing_stage='complete',
            device_type=self._get_device_type(device_id)
        ).observe(processing_duration)
    
    def record_model_inference(self, model_name: str, model_version: str, 
                             inference_duration: float, accuracy: float):
        """Record model inference metrics"""
        self.model_inference_duration.labels(
            model_name=model_name,
            model_version=model_version
        ).observe(inference_duration)
        
        self.model_accuracy.labels(
            model_name=model_name,
            dataset='current'
        ).set(accuracy)
    
    def update_device_status(self, device_id: str, device_type: str, 
                           connection_status: str):
        """Update device status metrics"""
        self.active_devices.labels(
            device_type=device_type,
            connection_status=connection_status
        ).inc() if connection_status == 'connected' else self.active_devices.labels(
            device_type=device_type,
            connection_status=connection_status
        ).dec()
    
    def record_data_quality(self, device_id: str, channel: int, quality_score: float):
        """Record data quality metrics"""
        self.data_quality_score.labels(
            device_id=device_id,
            channel=str(channel)
        ).set(quality_score)
    
    def record_compliance_violation(self, violation_type: str, severity: str, 
                                  tenant_id: str):
        """Record compliance violation"""
        self.compliance_violations.labels(
            violation_type=violation_type,
            severity=severity,
            tenant_id=tenant_id
        ).inc()
    
    def collect_system_metrics(self):
        """Collect system resource metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        for i, cpu in enumerate(cpu_percent):
            self.cpu_usage.labels(core=str(i)).set(cpu)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        self.memory_usage.labels(type='used').set(memory.used)
        self.memory_usage.labels(type='available').set(memory.available)
        self.memory_usage.labels(type='total').set(memory.total)
        
        # GPU metrics (if enabled and available)
        if self.config.enable_gpu_metrics:
            try:
                gpus = GPUtil.getGPUs()
                for gpu in gpus:
                    self.gpu_utilization.labels(
                        gpu_id=str(gpu.id),
                        gpu_name=gpu.name
                    ).set(gpu.load * 100)
                    
                    self.gpu_memory_usage.labels(
                        gpu_id=str(gpu.id),
                        type='used'
                    ).set(gpu.memoryUsed * 1024 * 1024)  # Convert to bytes
                    
                    self.gpu_memory_usage.labels(
                        gpu_id=str(gpu.id),
                        type='total'
                    ).set(gpu.memoryTotal * 1024 * 1024)
                    
            except Exception as e:
                logging.warning(f"Failed to collect GPU metrics: {e}")
    
    def _get_device_type(self, device_id: str) -> str:
        """Determine device type from device ID"""
        if 'openbci' in device_id.lower():
            return 'openbci'
        elif 'emotiv' in device_id.lower():
            return 'emotiv'
        elif 'gtec' in device_id.lower():
            return 'gtec'
        else:
            return 'unknown'
    
    def start_metrics_server(self):
        """Start Prometheus metrics server"""
        start_http_server(self.config.export_port)
        logging.info(f"Metrics server started on port {self.config.export_port}")
    
    async def continuous_collection(self):
        """Continuous metrics collection loop"""
        while True:
            try:
                if self.config.enable_system_metrics:
                    self.collect_system_metrics()
                
                await asyncio.sleep(self.config.collection_interval)
                
            except Exception as e:
                logging.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(1)  # Brief pause before retry

# Usage example
if __name__ == "__main__":
    import asyncio
    
    config = MetricsConfig(
        enable_gpu_metrics=True,
        enable_system_metrics=True,
        collection_interval=1.0,
        export_port=8080
    )
    
    metrics = EnterpriseMetrics(config)
    metrics.start_metrics_server()
    
    # Example of recording metrics
    metrics.record_signal_processing(
        device_id="openbci_001",
        channel_count=64,
        sampling_rate=1000,
        processing_duration=0.025
    )
    
    # Start continuous collection
    asyncio.run(metrics.continuous_collection())
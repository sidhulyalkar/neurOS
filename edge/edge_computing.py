# neuros/edge/edge_computing.py
"""
Edge Computing and Auto-scaling System for neurOS
Distributed processing with intelligent scaling
"""

import asyncio
import time
import json
import logging
import psutil
import docker
import kubernetes
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Types of compute nodes"""
    EDGE_DEVICE = "edge_device"
    CLOUD_INSTANCE = "cloud_instance"
    HYBRID_NODE = "hybrid_node"
    GPU_NODE = "gpu_node"

class ServiceStatus(Enum):
    """Service status states"""
    STARTING = "starting"
    RUNNING = "running"
    SCALING = "scaling"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]
    gpu_percent: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class EdgeNode:
    """Edge computing node"""
    node_id: str
    node_type: NodeType
    hostname: str
    ip_address: str
    port: int
    capabilities: List[str]
    resources: ResourceMetrics
    status: str = "healthy"
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceDefinition:
    """Service definition for deployment"""
    name: str
    image: str
    replicas: int
    cpu_request: float
    memory_request: int  # MB
    gpu_request: int = 0
    ports: List[int] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[Dict[str, str]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScalingRule:
    """Auto-scaling rule definition"""
    metric_name: str
    threshold_up: float
    threshold_down: float
    scale_up_by: int
    scale_down_by: int
    cooldown_seconds: int
    min_replicas: int
    max_replicas: int

class ResourceMonitor:
    """Monitor system resources"""
    
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history = 1000
    
    async def collect_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
            # GPU (if available)
            gpu_percent = 0.0
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_percent = gpus[0].load * 100
            except ImportError:
                pass
            
            metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                network_io=network_io,
                gpu_percent=gpu_percent
            )
            
            # Store in history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return ResourceMetrics(0, 0, 0, {})
    
    def get_average_metrics(self, minutes: int = 5) -> ResourceMetrics:
        """Get average metrics over time period"""
        if not self.metrics_history:
            return ResourceMetrics(0, 0, 0, {})
        
        # Get recent metrics
        recent_count = min(len(self.metrics_history), minutes * 2)  # 30s intervals
        recent_metrics = self.metrics_history[-recent_count:]
        
        avg_cpu = np.mean([m.cpu_percent for m in recent_metrics])
        avg_memory = np.mean([m.memory_percent for m in recent_metrics])
        avg_disk = np.mean([m.disk_percent for m in recent_metrics])
        avg_gpu = np.mean([m.gpu_percent for m in recent_metrics])
        
        return ResourceMetrics(
            cpu_percent=avg_cpu,
            memory_percent=avg_memory,
            disk_percent=avg_disk,
            network_io={},
            gpu_percent=avg_gpu
        )

class ContainerOrchestrator:
    """Container orchestration for edge services"""
    
    def __init__(self, use_kubernetes: bool = True):
        self.use_kubernetes = use_kubernetes
        self.docker_client = None
        self.k8s_client = None
        self.services: Dict[str, ServiceDefinition] = {}
        self.service_status: Dict[str, ServiceStatus] = {}
        
    async def initialize(self):
        """Initialize orchestrator"""
        if self.use_kubernetes:
            try:
                kubernetes.config.load_incluster_config()
                self.k8s_client = kubernetes.client.AppsV1Api()
                logger.info("Kubernetes client initialized")
            except:
                try:
                    kubernetes.config.load_kube_config()
                    self.k8s_client = kubernetes.client.AppsV1Api()
                    logger.info("Kubernetes client initialized (local config)")
                except Exception as e:
                    logger.warning(f"Kubernetes initialization failed: {e}")
                    self.use_kubernetes = False
        
        if not self.use_kubernetes:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized")
            except Exception as e:
                logger.error(f"Docker initialization failed: {e}")
    
    async def deploy_service(self, service: ServiceDefinition) -> bool:
        """Deploy a service"""
        try:
            self.services[service.name] = service
            self.service_status[service.name] = ServiceStatus.STARTING
            
            if self.use_kubernetes and self.k8s_client:
                success = await self._deploy_k8s_service(service)
            elif self.docker_client:
                success = await self._deploy_docker_service(service)
            else:
                logger.error("No orchestrator available")
                return False
            
            if success:
                self.service_status[service.name] = ServiceStatus.RUNNING
                logger.info(f"Service {service.name} deployed successfully")
            else:
                self.service_status[service.name] = ServiceStatus.ERROR
                logger.error(f"Service {service.name} deployment failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Service deployment failed: {e}")
            self.service_status[service.name] = ServiceStatus.ERROR
            return False
    
    async def _deploy_k8s_service(self, service: ServiceDefinition) -> bool:
        """Deploy service to Kubernetes"""
        try:
            # Create deployment manifest
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": service.name, "namespace": "neuros-edge"},
                "spec": {
                    "replicas": service.replicas,
                    "selector": {"matchLabels": {"app": service.name}},
                    "template": {
                        "metadata": {"labels": {"app": service.name}},
                        "spec": {
                            "containers": [{
                                "name": service.name,
                                "image": service.image,
                                "ports": [{"containerPort": port} for port in service.ports],
                                "env": [{"name": k, "value": v} for k, v in service.environment.items()],
                                "resources": {
                                    "requests": {
                                        "cpu": f"{service.cpu_request}",
                                        "memory": f"{service.memory_request}Mi"
                                    }
                                }
                            }]
                        }
                    }
                }
            }
            
            # Add GPU resources if requested
            if service.gpu_request > 0:
                deployment["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["nvidia.com/gpu"] = service.gpu_request
            
            # Apply deployment
            self.k8s_client.create_namespaced_deployment(
                namespace="neuros-edge",
                body=deployment
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Kubernetes deployment failed: {e}")
            return False
    
    async def _deploy_docker_service(self, service: ServiceDefinition) -> bool:
        """Deploy service to Docker"""
        try:
            # Prepare environment
            environment = service.environment.copy()
            
            # Prepare ports
            ports = {f"{port}/tcp": port for port in service.ports} if service.ports else None
            
            # Prepare volumes
            volumes = {}
            for volume in service.volumes:
                volumes[volume["host_path"]] = {"bind": volume["container_path"], "mode": "rw"}
            
            # Run containers for replicas
            for i in range(service.replicas):
                container_name = f"{service.name}-{i}"
                
                self.docker_client.containers.run(
                    service.image,
                    name=container_name,
                    environment=environment,
                    ports=ports,
                    volumes=volumes,
                    detach=True,
                    restart_policy={"Name": "unless-stopped"}
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            return False
    
    async def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale service to specified replicas"""
        if service_name not in self.services:
            return False
        
        try:
            self.service_status[service_name] = ServiceStatus.SCALING
            
            if self.use_kubernetes and self.k8s_client:
                success = await self._scale_k8s_service(service_name, replicas)
            elif self.docker_client:
                success = await self._scale_docker_service(service_name, replicas)
            else:
                return False
            
            if success:
                self.services[service_name].replicas = replicas
                self.service_status[service_name] = ServiceStatus.RUNNING
                logger.info(f"Service {service_name} scaled to {replicas} replicas")
            else:
                self.service_status[service_name] = ServiceStatus.ERROR
            
            return success
            
        except Exception as e:
            logger.error(f"Service scaling failed: {e}")
            self.service_status[service_name] = ServiceStatus.ERROR
            return False
    
    async def _scale_k8s_service(self, service_name: str, replicas: int) -> bool:
        """Scale Kubernetes service"""
        try:
            # Patch deployment
            body = {"spec": {"replicas": replicas}}
            self.k8s_client.patch_namespaced_deployment_scale(
                name=service_name,
                namespace="neuros-edge",
                body=body
            )
            return True
        except Exception as e:
            logger.error(f"Kubernetes scaling failed: {e}")
            return False
    
    async def _scale_docker_service(self, service_name: str, replicas: int) -> bool:
        """Scale Docker service"""
        try:
            # Get current containers
            current_containers = [
                c for c in self.docker_client.containers.list(all=True)
                if c.name.startswith(f"{service_name}-")
            ]
            
            current_count = len(current_containers)
            
            if replicas > current_count:
                # Scale up
                service = self.services[service_name]
                for i in range(current_count, replicas):
                    container_name = f"{service_name}-{i}"
                    self.docker_client.containers.run(
                        service.image,
                        name=container_name,
                        environment=service.environment,
                        detach=True,
                        restart_policy={"Name": "unless-stopped"}
                    )
            elif replicas < current_count:
                # Scale down
                containers_to_remove = current_containers[replicas:]
                for container in containers_to_remove:
                    container.stop()
                    container.remove()
            
            return True
            
        except Exception as e:
            logger.error(f"Docker scaling failed: {e}")
            return False
    
    async def get_service_metrics(self, service_name: str) -> Dict[str, Any]:
        """Get service metrics"""
        if service_name not in self.services:
            return {}
        
        try:
            if self.use_kubernetes and self.k8s_client:
                return await self._get_k8s_service_metrics(service_name)
            elif self.docker_client:
                return await self._get_docker_service_metrics(service_name)
            else:
                return {}
        except Exception as e:
            logger.error(f"Failed to get service metrics: {e}")
            return {}
    
    async def _get_docker_service_metrics(self, service_name: str) -> Dict[str, Any]:
        """Get Docker service metrics"""
        containers = [
            c for c in self.docker_client.containers.list()
            if c.name.startswith(f"{service_name}-")
        ]
        
        metrics = {
            "replica_count": len(containers),
            "running_replicas": sum(1 for c in containers if c.status == "running"),
            "cpu_usage": 0.0,
            "memory_usage": 0.0
        }
        
        for container in containers:
            try:
                stats = container.stats(stream=False)
                # Parse CPU and memory usage from stats
                # Simplified calculation
                metrics["cpu_usage"] += 50.0  # Mock value
                metrics["memory_usage"] += 100.0  # Mock value
            except:
                pass
        
        return metrics

class AutoScaler:
    """Automatic scaling based on metrics"""
    
    def __init__(self, orchestrator: ContainerOrchestrator, monitor: ResourceMonitor):
        self.orchestrator = orchestrator
        self.monitor = monitor
        self.scaling_rules: Dict[str, List[ScalingRule]] = {}
        self.last_scaling: Dict[str, datetime] = {}
        self.enabled = True
    
    def add_scaling_rule(self, service_name: str, rule: ScalingRule):
        """Add scaling rule for service"""
        if service_name not in self.scaling_rules:
            self.scaling_rules[service_name] = []
        self.scaling_rules[service_name].append(rule)
        logger.info(f"Added scaling rule for {service_name}: {rule.metric_name}")
    
    async def evaluate_scaling(self):
        """Evaluate scaling rules for all services"""
        if not self.enabled:
            return
        
        for service_name, rules in self.scaling_rules.items():
            if service_name not in self.orchestrator.services:
                continue
            
            # Check cooldown
            if service_name in self.last_scaling:
                time_since_scaling = datetime.now() - self.last_scaling[service_name]
                if time_since_scaling.total_seconds() < 300:  # 5 minute default cooldown
                    continue
            
            # Get current metrics
            service_metrics = await self.orchestrator.get_service_metrics(service_name)
            system_metrics = self.monitor.get_average_metrics()
            
            current_replicas = self.orchestrator.services[service_name].replicas
            
            for rule in rules:
                metric_value = self._get_metric_value(rule.metric_name, service_metrics, system_metrics)
                
                if metric_value is None:
                    continue
                
                # Evaluate scaling decisions
                should_scale_up = (
                    metric_value > rule.threshold_up and
                    current_replicas < rule.max_replicas
                )
                
                should_scale_down = (
                    metric_value < rule.threshold_down and
                    current_replicas > rule.min_replicas
                )
                
                if should_scale_up:
                    new_replicas = min(
                        current_replicas + rule.scale_up_by,
                        rule.max_replicas
                    )
                    await self._perform_scaling(service_name, new_replicas, "up", rule)
                    break  # Only apply one rule at a time
                
                elif should_scale_down:
                    new_replicas = max(
                        current_replicas - rule.scale_down_by,
                        rule.min_replicas
                    )
                    await self._perform_scaling(service_name, new_replicas, "down", rule)
                    break  # Only apply one rule at a time
    
    def _get_metric_value(self, metric_name: str, service_metrics: Dict, system_metrics: ResourceMetrics) -> Optional[float]:
        """Get metric value by name"""
        if metric_name == "cpu_usage":
            return system_metrics.cpu_percent
        elif metric_name == "memory_usage":
            return system_metrics.memory_percent
        elif metric_name == "gpu_usage":
            return system_metrics.gpu_percent
        elif metric_name == "replica_cpu":
            return service_metrics.get("cpu_usage", 0) / max(service_metrics.get("replica_count", 1), 1)
        elif metric_name == "request_rate":
            return service_metrics.get("request_rate", 0)
        else:
            return service_metrics.get(metric_name)
    
    async def _perform_scaling(self, service_name: str, new_replicas: int, direction: str, rule: ScalingRule):
        """Perform scaling operation"""
        current_replicas = self.orchestrator.services[service_name].replicas
        
        logger.info(
            f"Auto-scaling {service_name} {direction}: {current_replicas} -> {new_replicas} "
            f"(rule: {rule.metric_name})"
        )
        
        success = await self.orchestrator.scale_service(service_name, new_replicas)
        
        if success:
            self.last_scaling[service_name] = datetime.now()
        else:
            logger.error(f"Auto-scaling failed for {service_name}")

class EdgeComputingManager:
    """Main edge computing management system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.nodes: Dict[str, EdgeNode] = {}
        self.monitor = ResourceMonitor()
        self.orchestrator = ContainerOrchestrator()
        self.autoscaler = AutoScaler(self.orchestrator, self.monitor)
        
        self.heartbeat_interval = 30
        self.metrics_collection_task = None
        self.autoscaling_task = None
        self.heartbeat_task = None
    
    async def initialize(self):
        """Initialize edge computing system"""
        logger.info("Initializing edge computing system...")
        
        await self.orchestrator.initialize()
        
        # Start background tasks
        self.metrics_collection_task = asyncio.create_task(self._metrics_collection_loop())
        self.autoscaling_task = asyncio.create_task(self._autoscaling_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Register local node
        await self._register_local_node()
        
        logger.info("Edge computing system initialized")
    
    async def _register_local_node(self):
        """Register local node"""
        import socket
        
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Detect capabilities
        capabilities = ["bci_processing"]
        if psutil.virtual_memory().total > 8 * 1024**3:  # > 8GB RAM
            capabilities.append("ml_training")
        
        try:
            import GPUtil
            if GPUtil.getGPUs():
                capabilities.append("gpu_processing")
        except ImportError:
            pass
        
        initial_metrics = await self.monitor.collect_metrics()
        
        node = EdgeNode(
            node_id=f"local_{hostname}",
            node_type=NodeType.HYBRID_NODE,
            hostname=hostname,
            ip_address=ip_address,
            port=8000,
            capabilities=capabilities,
            resources=initial_metrics
        )
        
        self.nodes[node.node_id] = node
        logger.info(f"Registered local node: {node.node_id}")
    
    async def _metrics_collection_loop(self):
        """Background task for metrics collection"""
        while True:
            try:
                await self.monitor.collect_metrics()
                await asyncio.sleep(self.monitor.collection_interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)
    
    async def _autoscaling_loop(self):
        """Background task for auto-scaling"""
        while True:
            try:
                await self.autoscaler.evaluate_scaling()
                await asyncio.sleep(60)  # Evaluate every minute
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
                await asyncio.sleep(60)
    
    async def _heartbeat_loop(self):
        """Background task for node heartbeats"""
        while True:
            try:
                # Update local node metrics
                for node_id, node in self.nodes.items():
                    if node_id.startswith("local_"):
                        node.resources = await self.monitor.collect_metrics()
                        node.last_heartbeat = datetime.now()
                
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)
    
    async def deploy_bci_service(self, service_config: Dict[str, Any]) -> bool:
        """Deploy BCI processing service"""
        service = ServiceDefinition(
            name=service_config["name"],
            image=service_config.get("image", "neuros/bci-processor:latest"),
            replicas=service_config.get("replicas", 1),
            cpu_request=service_config.get("cpu_request", 0.5),
            memory_request=service_config.get("memory_request", 512),
            gpu_request=service_config.get("gpu_request", 0),
            ports=service_config.get("ports", [8080]),
            environment=service_config.get("environment", {}),
            constraints=service_config.get("constraints", {})
        )
        
        # Add auto-scaling rules
        if service_config.get("auto_scaling", {}).get("enabled", False):
            scaling_config = service_config["auto_scaling"]
            
            rule = ScalingRule(
                metric_name=scaling_config.get("metric", "cpu_usage"),
                threshold_up=scaling_config.get("scale_up_threshold", 70.0),
                threshold_down=scaling_config.get("scale_down_threshold", 30.0),
                scale_up_by=scaling_config.get("scale_up_by", 1),
                scale_down_by=scaling_config.get("scale_down_by", 1),
                cooldown_seconds=scaling_config.get("cooldown", 300),
                min_replicas=scaling_config.get("min_replicas", 1),
                max_replicas=scaling_config.get("max_replicas", 10)
            )
            
            self.autoscaler.add_scaling_rule(service.name, rule)
        
        return await self.orchestrator.deploy_service(service)
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status and metrics"""
        total_nodes = len(self.nodes)
        healthy_nodes = sum(1 for node in self.nodes.values() if node.status == "healthy")
        
        # Aggregate resources
        total_cpu = 0
        total_memory = 0
        total_gpu = 0
        
        for node in self.nodes.values():
            total_cpu += node.resources.cpu_percent
            total_memory += node.resources.memory_percent
            if hasattr(node.resources, 'gpu_percent'):
                total_gpu += node.resources.gpu_percent
        
        avg_cpu = total_cpu / max(total_nodes, 1)
        avg_memory = total_memory / max(total_nodes, 1)
        avg_gpu = total_gpu / max(total_nodes, 1)
        
        # Service status
        services = {}
        for service_name, service in self.orchestrator.services.items():
            services[service_name] = {
                "replicas": service.replicas,
                "status": self.orchestrator.service_status.get(service_name, ServiceStatus.UNKNOWN).value,
                "image": service.image
            }
        
        return {
            "cluster": {
                "total_nodes": total_nodes,
                "healthy_nodes": healthy_nodes,
                "avg_cpu_usage": avg_cpu,
                "avg_memory_usage": avg_memory,
                "avg_gpu_usage": avg_gpu
            },
            "services": services,
            "autoscaling": {
                "enabled": self.autoscaler.enabled,
                "rules_count": sum(len(rules) for rules in self.autoscaler.scaling_rules.values())
            }
        }
    
    async def shutdown(self):
        """Shutdown edge computing system"""
        logger.info("Shutting down edge computing system...")
        
        # Cancel background tasks
        if self.metrics_collection_task:
            self.metrics_collection_task.cancel()
        if self.autoscaling_task:
            self.autoscaling_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        logger.info("Edge computing system shutdown complete")

# Configuration templates
EDGE_SERVICE_CONFIGS = {
    "bci_realtime_processor": {
        "name": "bci-realtime-processor",
        "image": "neuros/bci-processor:latest",
        "replicas": 2,
        "cpu_request": 1.0,
        "memory_request": 1024,
        "gpu_request": 0,
        "ports": [8080, 8081],
        "environment": {
            "NEUROS_MODE": "realtime",
            "LOG_LEVEL": "INFO"
        },
        "auto_scaling": {
            "enabled": True,
            "metric": "cpu_usage",
            "scale_up_threshold": 75.0,
            "scale_down_threshold": 25.0,
            "min_replicas": 1,
            "max_replicas": 8
        }
    },
    "ml_training_service": {
        "name": "ml-training-service",
        "image": "neuros/ml-trainer:latest",
        "replicas": 1,
        "cpu_request": 2.0,
        "memory_request": 4096,
        "gpu_request": 1,
        "ports": [8090],
        "environment": {
            "NEUROS_MODE": "training",
            "CUDA_VISIBLE_DEVICES": "0"
        },
        "auto_scaling": {
            "enabled": True,
            "metric": "gpu_usage",
            "scale_up_threshold": 80.0,
            "scale_down_threshold": 20.0,
            "min_replicas": 0,
            "max_replicas": 4
        }
    },
    "data_collector": {
        "name": "data-collector",
        "image": "neuros/data-collector:latest",
        "replicas": 1,
        "cpu_request": 0.5,
        "memory_request": 512,
        "ports": [8070],
        "environment": {
            "BUFFER_SIZE": "10000",
            "SAMPLING_RATE": "250"
        },
        "auto_scaling": {
            "enabled": False
        }
    }
}

# Kubernetes manifests
def generate_k8s_manifests(service: ServiceDefinition) -> List[Dict[str, Any]]:
    """Generate Kubernetes manifests for service"""
    manifests = []
    
    # Deployment
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": service.name,
            "namespace": "neuros-edge",
            "labels": {
                "app": service.name,
                "component": "neuros",
                "version": "1.0.0"
            }
        },
        "spec": {
            "replicas": service.replicas,
            "strategy": {
                "type": "RollingUpdate",
                "rollingUpdate": {
                    "maxUnavailable": 1,
                    "maxSurge": 1
                }
            },
            "selector": {
                "matchLabels": {"app": service.name}
            },
            "template": {
                "metadata": {
                    "labels": {"app": service.name}
                },
                "spec": {
                    "containers": [{
                        "name": service.name,
                        "image": service.image,
                        "ports": [{"containerPort": port} for port in service.ports],
                        "env": [{"name": k, "value": v} for k, v in service.environment.items()],
                        "resources": {
                            "requests": {
                                "cpu": f"{service.cpu_request}",
                                "memory": f"{service.memory_request}Mi"
                            },
                            "limits": {
                                "cpu": f"{service.cpu_request * 2}",
                                "memory": f"{service.memory_request * 2}Mi"
                            }
                        },
                        "livenessProbe": {
                            "httpGet": {"path": "/health", "port": service.ports[0] if service.ports else 8080},
                            "initialDelaySeconds": 30,
                            "periodSeconds": 10
                        },
                        "readinessProbe": {
                            "httpGet": {"path": "/ready", "port": service.ports[0] if service.ports else 8080},
                            "initialDelaySeconds": 5,
                            "periodSeconds": 5
                        }
                    }],
                    "restartPolicy": "Always"
                }
            }
        }
    }
    
    # Add GPU resources if requested
    if service.gpu_request > 0:
        gpu_resources = {"nvidia.com/gpu": service.gpu_request}
        deployment["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"].update(gpu_resources)
        deployment["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"].update(gpu_resources)
    
    manifests.append(deployment)
    
    # Service
    if service.ports:
        k8s_service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service.name,
                "namespace": "neuros-edge",
                "labels": {"app": service.name}
            },
            "spec": {
                "selector": {"app": service.name},
                "ports": [
                    {"port": port, "targetPort": port, "name": f"port-{port}"}
                    for port in service.ports
                ],
                "type": "ClusterIP"
            }
        }
        manifests.append(k8s_service)
    
    return manifests

# CLI interface for edge computing
class EdgeComputingCLI:
    """Command-line interface for edge computing"""
    
    def __init__(self, manager: EdgeComputingManager):
        self.manager = manager
    
    async def deploy_command(self, service_name: str, config_file: str = None):
        """Deploy service command"""
        if config_file:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        elif service_name in EDGE_SERVICE_CONFIGS:
            config = EDGE_SERVICE_CONFIGS[service_name]
        else:
            print(f"❌ Unknown service: {service_name}")
            return
        
        print(f"🚀 Deploying service: {service_name}")
        success = await self.manager.deploy_bci_service(config)
        
        if success:
            print(f"✅ Service {service_name} deployed successfully")
        else:
            print(f"❌ Service {service_name} deployment failed")
    
    async def status_command(self):
        """Show cluster status"""
        status = await self.manager.get_cluster_status()
        
        print("\n🖥️  Edge Computing Cluster Status")
        print("=" * 50)
        
        cluster = status["cluster"]
        print(f"Nodes: {cluster['healthy_nodes']}/{cluster['total_nodes']} healthy")
        print(f"Avg CPU Usage: {cluster['avg_cpu_usage']:.1f}%")
        print(f"Avg Memory Usage: {cluster['avg_memory_usage']:.1f}%")
        print(f"Avg GPU Usage: {cluster['avg_gpu_usage']:.1f}%")
        
        print(f"\nServices: {len(status['services'])}")
        for name, service in status["services"].items():
            status_icon = "✅" if service["status"] == "running" else "❌"
            print(f"  {status_icon} {name}: {service['replicas']} replicas ({service['status']})")
        
        print(f"\nAuto-scaling: {'✅ Enabled' if status['autoscaling']['enabled'] else '❌ Disabled'}")
        print(f"Scaling rules: {status['autoscaling']['rules_count']}")
    
    async def scale_command(self, service_name: str, replicas: int):
        """Scale service command"""
        print(f"📏 Scaling {service_name} to {replicas} replicas...")
        success = await self.manager.orchestrator.scale_service(service_name, replicas)
        
        if success:
            print(f"✅ Service {service_name} scaled successfully")
        else:
            print(f"❌ Service {service_name} scaling failed")
    
    async def logs_command(self, service_name: str, lines: int = 50):
        """Show service logs"""
        print(f"📜 Logs for {service_name} (last {lines} lines):")
        print("=" * 50)
        
        # Mock logs for demonstration
        import datetime
        now = datetime.datetime.now()
        
        for i in range(lines):
            timestamp = (now - datetime.timedelta(minutes=i)).strftime("%H:%M:%S")
            log_line = f"[{timestamp}] INFO - Processing BCI data batch {i+1}"
            print(log_line)

# Integration with FastAPI
def add_edge_computing_routes(app, edge_manager: EdgeComputingManager):
    """Add edge computing routes to FastAPI app"""
    
    @app.get("/edge/status")
    async def get_edge_status():
        """Get edge computing status"""
        return await edge_manager.get_cluster_status()
    
    @app.post("/edge/deploy")
    async def deploy_edge_service(config: Dict[str, Any]):
        """Deploy edge service"""
        try:
            success = await edge_manager.deploy_bci_service(config)
            return {"success": success, "message": "Service deployed" if success else "Deployment failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.post("/edge/scale/{service_name}")
    async def scale_edge_service(service_name: str, replicas: int):
        """Scale edge service"""
        try:
            success = await edge_manager.orchestrator.scale_service(service_name, replicas)
            return {"success": success, "message": f"Scaled to {replicas} replicas" if success else "Scaling failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.get("/edge/metrics")
    async def get_edge_metrics():
        """Get edge computing metrics"""
        metrics = edge_manager.monitor.get_average_metrics()
        return {
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "disk_percent": metrics.disk_percent,
            "gpu_percent": metrics.gpu_percent,
            "timestamp": datetime.now().isoformat()
        }

# Example usage
async def main():
    """Example usage of edge computing system"""
    
    # Initialize edge computing manager
    config = {
        "use_kubernetes": True,
        "monitoring_interval": 30,
        "autoscaling_enabled": True
    }
    
    edge_manager = EdgeComputingManager(config)
    await edge_manager.initialize()
    
    # Deploy BCI services
    for service_name, service_config in EDGE_SERVICE_CONFIGS.items():
        print(f"Deploying {service_name}...")
        success = await edge_manager.deploy_bci_service(service_config)
        print(f"{'✅' if success else '❌'} {service_name}")
    
    # Run for a while
    try:
        print("Edge computing system running... (Ctrl+C to stop)")
        while True:
            await asyncio.sleep(60)
            status = await edge_manager.get_cluster_status()
            print(f"Status: {status['cluster']['healthy_nodes']} nodes, {len(status['services'])} services")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await edge_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
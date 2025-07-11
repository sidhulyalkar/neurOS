# 🧠 neurOS - The Operating System for Brain-Computer Interfaces

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B.svg)](https://streamlit.io)

**Enterprise-grade BCI development, deployment, and management platform**

[🚀 Quick Start](#-quick-start) • [📚 Documentation](#-documentation) • [🌟 Features](#-features) • [🏗️ Architecture](#-architecture) • [🤝 Contributing](#-contributing)

</div>

---

## 🧠 What is neurOS?

neurOS is the world's first **complete operating system designed specifically for Brain-Computer Interfaces**. It provides a comprehensive, enterprise-ready platform for researchers, developers, and organizations to build, deploy, and manage BCI applications at scale.

### 🎯 Key Highlights

- **🏢 Enterprise-Ready**: Production-grade architecture with security, compliance, and scalability
- **⚡ Real-time Processing**: Sub-100ms latency for real-time BCI applications
- **🔌 Extensible**: Plugin architecture for custom components and integrations
- **👥 Collaborative**: Multi-user real-time sessions with live sharing
- **🖥️ Edge Computing**: Auto-scaling distributed processing with Kubernetes/Docker
- **📊 Analytics**: Advanced monitoring, insights, and predictive analytics
- **🌐 API-First**: Comprehensive REST API with WebSocket support
- **🔒 Secure**: Enterprise-grade security with audit logging and compliance

---

## 🌟 Features

### 🔧 **Core BCI Capabilities**
- **Multi-modal Signal Support**: EEG, ECoG, EMG, EOG processing
- **Real-time Processing**: Sub-100ms latency guarantee
- **Advanced Signal Processing**: Filtering, artifact removal, spatial processing
- **Machine Learning**: Multiple algorithms with automated hyperparameter tuning
- **Hardware Agnostic**: Support for OpenBCI, g.tec, Emotiv, NeuroSky, and custom devices

### 🏗️ **Enterprise Architecture**
- **🔌 Plugin System**: Hot-loading extensible components
- **🌐 REST API Gateway**: Authentication, rate limiting, monitoring
- **👥 Real-time Collaboration**: Multi-user sessions with live sharing
- **🖥️ Edge Computing**: Kubernetes/Docker orchestration with auto-scaling
- **📊 Advanced Analytics**: Performance monitoring and predictive insights
- **🔒 Enterprise Security**: RBAC, audit logging, encryption, compliance

### 🚀 **Developer Experience**
- **Complete CLI**: Unified command interface for all operations
- **Interactive Dashboard**: Real-time monitoring and management
- **Plugin SDK**: Easy development of custom components
- **Comprehensive API**: Full REST API with auto-generated documentation
- **Testing Suite**: Automated validation and deployment tools

### 🌍 **Deployment Options**
- **Local Development**: Quick setup for research and prototyping
- **Docker Containers**: Portable deployment across environments
- **Kubernetes**: Production-scale orchestration and auto-scaling
- **Cloud Ready**: AWS, Azure, GCP integration
- **Edge Computing**: Distributed processing at the edge

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** (3.11 or 3.12 recommended)
- **8GB+ RAM** (16GB+ recommended)
- **4+ CPU cores** (for optimal performance)

### Installation

#### Option 1: Basic Installation
```bash
# Clone the repository
git clone https://github.com/neurOS/neurOS.git
cd neurOS

# Install dependencies
pip install -r requirements.txt

# Install neurOS in development mode
pip install -e .

# Verify installation
neuros --version
```

#### Option 2: Feature-Specific Installation
```bash
# Core installation
pip install -e .

# With GPU support
pip install -e ".[gpu]"

# With container orchestration
pip install -e ".[orchestration]"

# With all features
pip install -e ".[all]"

# Development setup
pip install -e ".[dev]"
```

### First Steps

#### 1. Check System Status
```bash
neuros status
```

#### 2. Start the Complete System
```bash
# Start the neurOS server (API + all services)
neuros serve

# Access the system:
# 🌐 API: http://localhost:8000
# 📊 Dashboard: http://localhost:8501
# 📖 API Docs: http://localhost:8000/docs
```

#### 3. Launch Analytics Dashboard
```bash
# In a new terminal
neuros dashboard
# Opens advanced analytics at http://localhost:8501
```

#### 4. Your First BCI Pipeline
```python
from neuros.core.pipeline import EnhancedPipeline, PipelineConfig

# Create a real-time BCI pipeline
config = PipelineConfig(
    name="my_first_bci_pipeline",
    mode="realtime",
    latency_target_ms=50,
    channels=8,
    sampling_rate=250
)

pipeline = EnhancedPipeline(config)
await pipeline.initialize()

# Start processing
await pipeline.start()
```

---

## 🏗️ Architecture

neurOS follows a modular, microservices architecture designed for enterprise deployment:

```
🧠 neurOS Enterprise Architecture
├── 🔌 Plugin System          # Extensible components
├── 🌐 API Gateway            # Authentication, rate limiting, routing
├── 👥 Collaboration Engine   # Real-time multi-user sessions
├── 🖥️  Edge Computing        # Auto-scaling distributed processing
├── 📊 Analytics Engine       # Monitoring, insights, predictions
├── 🔒 Security Layer         # RBAC, audit, encryption, compliance
├── ⚡ Real-time Processor    # Sub-100ms BCI processing
├── 🤖 AI Agent Framework     # Intelligent optimization and automation
├── 🎛️  Interactive Dashboard # Live monitoring and management
└── 🚀 Unified CLI            # Complete command-line interface
```

### Core Components

#### 🔌 **Plugin Architecture**
- **Hot-loading**: Load/unload plugins without restart
- **Security**: Sandboxed execution with permission system
- **Types**: Signal processors, feature extractors, classifiers, hardware interfaces
- **SDK**: Easy development with comprehensive documentation

#### 🌐 **API Gateway**
- **Authentication**: JWT with refresh tokens, MFA support
- **Rate Limiting**: Redis-based with configurable policies
- **Monitoring**: Request/response logging, metrics, health checks
- **WebSocket**: Real-time streaming and collaboration

#### 👥 **Real-time Collaboration**
- **Multi-user Sessions**: Up to 50 concurrent users per session
- **Live Sharing**: Pipelines, data streams, annotations
- **Communication**: Integrated chat, cursor tracking
- **Permissions**: Role-based access control

#### 🖥️ **Edge Computing**
- **Orchestration**: Kubernetes and Docker support
- **Auto-scaling**: CPU, memory, and custom metric-based
- **Load Balancing**: Intelligent traffic distribution
- **Health Management**: Automatic recovery and failover

---

## 📚 Documentation

### 🎯 **Getting Started**
- [Installation Guide](docs/installation.md)
- [Quick Start Tutorial](docs/quickstart.md)
- [Your First BCI Application](docs/first-app.md)
- [Configuration Guide](docs/configuration.md)

### 🔧 **Development**
- [Plugin Development](docs/plugins.md)
- [API Reference](docs/api.md)
- [CLI Reference](docs/cli.md)
- [Testing Guide](docs/testing.md)

### 🏢 **Enterprise**
- [Deployment Guide](docs/deployment.md)
- [Security & Compliance](docs/security.md)
- [Monitoring & Analytics](docs/monitoring.md)
- [Scaling & Performance](docs/scaling.md)

### 🧠 **BCI Specific**
- [Signal Processing](docs/signal-processing.md)
- [Machine Learning](docs/machine-learning.md)
- [Hardware Integration](docs/hardware.md)
- [Real-time Systems](docs/realtime.md)

---

## 🎮 Usage Examples

### CLI Operations
```bash
# System management
neuros status                    # Check system status
neuros serve                     # Start complete server
neuros dashboard                 # Launch analytics dashboard

# Plugin management
neuros plugins list              # List available plugins
neuros plugins install ./my-plugin  # Install custom plugin
neuros plugins enable signal-filter # Enable a plugin

# Edge computing
neuros edge status               # Show cluster status
neuros edge deploy bci-processor # Deploy BCI service
neuros edge scale ml-trainer 4  # Scale to 4 replicas

# Collaboration
neuros collab create "Research Session"  # Create session
neuros collab list               # List active sessions

# Analytics
neuros analytics report          # Generate system report
neuros analytics report --format json  # JSON format
```

### Python API
```python
import asyncio
from neuros import neurOS

async def main():
    # Initialize neurOS
    system = neurOS()
    await system.initialize()
    
    # Create and deploy a BCI service
    service_config = {
        "name": "realtime-bci",
        "image": "neuros/bci-processor:latest",
        "replicas": 2,
        "auto_scaling": {
            "enabled": True,
            "min_replicas": 1,
            "max_replicas": 10,
            "cpu_threshold": 70
        }
    }
    
    await system.edge.deploy_service(service_config)
    
    # Start real-time collaboration session
    session_id = await system.collaboration.create_session(
        created_by="researcher_1",
        name="Motor Imagery Study"
    )
    
    # Generate analytics report
    report = await system.analytics.generate_report()
    print(f"System processing {report['throughput']} samples
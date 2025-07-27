# frontend/ultimate_dashboard.py
"""
Ultimate neurOS Dashboard - Complete BCI Operating System Interface
Combines monitoring, analytics, security, social features, and data playground
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import networkx as nx
import io
import base64

# Configure page
st.set_page_config(
    page_title="neurOS - Ultimate Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for ultimate dashboard
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%);
        padding: 1.2rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.15);
    }
    
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    
    .status-running { background: linear-gradient(45deg, #4CAF50, #45a049); }
    .status-stopped { background: linear-gradient(45deg, #f44336, #da190b); }
    .status-warning { background: linear-gradient(45deg, #ff9800, #f57c00); }
    .status-idle { background: linear-gradient(45deg, #9E9E9E, #757575); }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.1); }
    }
    
    .component-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .component-card:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        border-color: #667eea;
    }
    
    .social-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #10b981;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    .peer-reviewed {
        border-left-color: #3b82f6;
    }
    
    .trending {
        border-left-color: #f59e0b;
    }
    
    .tab-container {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    .model-viz {
        background: linear-gradient(135deg, #fef7ff 0%, #f3e8ff 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #d8b4fe;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize comprehensive session state
def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'realtime_enabled': True,
        'connected_devices': ["OpenBCI Cyton", "Emotiv EPOC", "g.tec Nautilus"],
        'active_pipelines': [],
        'ai_agents_running': True,
        'user_settings': {
            'theme': 'dark',
            'refresh_rate': 1000,
            'notifications': True,
            'auto_save': True
        },
        'social_feed': [],
        'current_experiments': [],
        'model_training_progress': {},
        'system_health': {
            'cpu_usage': 45.2,
            'memory_usage': 62.8,
            'gpu_usage': 78.3,
            'disk_usage': 34.1
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def main():
    """Main dashboard application"""
    initialize_session_state()
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🧠 neurOS Ultimate Dashboard</h1>
        <p>Complete Brain-Computer Interface Operating System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for different sections
    tabs = st.tabs([
        "🏠 Monitor", "📊 Analytics", "🧪 Data Playground", "🌐 NeuroSocial", 
        "🔒 Security", "⚙️ Settings", "🔗 Connections", "🛠️ Hardware"
    ])
    
    with tabs[0]:  # Monitor
        show_monitor_dashboard()
    
    with tabs[1]:  # Analytics
        show_analytics_dashboard()
    
    with tabs[2]:  # Data Playground
        show_data_playground()
    
    with tabs[3]:  # NeuroSocial
        show_neurosocial_feed()
    
    with tabs[4]:  # Security
        show_security_dashboard()
    
    with tabs[5]:  # Settings
        show_settings_dashboard()
    
    with tabs[6]:  # Connections
        show_connections_dashboard()
    
    with tabs[7]:  # Hardware
        show_hardware_dashboard()

def show_monitor_dashboard():
    """Real-time monitoring dashboard"""
    st.header("🏠 System Monitor")
    
    # System overview metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    metrics = [
        ("Latency", "47.2ms", "-2.1ms", "🚀"),
        ("Throughput", "248/s", "+12", "📈"),
        ("Accuracy", "94.7%", "+1.2%", "🎯"),
        ("Devices", len(st.session_state.connected_devices), "0", "🔌"),
        ("Uptime", "2d 14h", "+24h", "⏱️")
    ]
    
    for i, (label, value, delta, icon) in enumerate(metrics):
        with [col1, col2, col3, col4, col5][i]:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(f"{icon} {label}", value, delta)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Real-time charts
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Live Performance Metrics")
        
        # Generate real-time data
        time_points = pd.date_range(start=datetime.now() - timedelta(minutes=30), 
                                   end=datetime.now(), freq='10S')
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Latency (ms)', 'Throughput (samples/s)', 'CPU Usage (%)', 'Memory Usage (%)'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Generate synthetic data
        latency = 47 + np.sin(np.arange(len(time_points))/10) * 5 + np.random.normal(0, 2, len(time_points))
        throughput = 250 + np.cos(np.arange(len(time_points))/8) * 20 + np.random.normal(0, 5, len(time_points))
        cpu = st.session_state.system_health['cpu_usage'] + np.random.normal(0, 5, len(time_points))
        memory = st.session_state.system_health['memory_usage'] + np.random.normal(0, 3, len(time_points))
        
        # Add traces
        fig.add_trace(go.Scatter(x=time_points, y=latency, name='Latency', 
                                line=dict(color='#ff6b6b', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=time_points, y=throughput, name='Throughput', 
                                line=dict(color='#4ecdc4', width=2)), row=1, col=2)
        fig.add_trace(go.Scatter(x=time_points, y=cpu, name='CPU', 
                                line=dict(color='#45b7d1', width=2), fill='tonexty'), row=2, col=1)
        fig.add_trace(go.Scatter(x=time_points, y=memory, name='Memory', 
                                line=dict(color='#96ceb4', width=2), fill='tonexty'), row=2, col=2)
        
        fig.update_layout(height=500, showlegend=False, title_text="Real-time System Performance")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎛️ System Status")
        
        # System components
        components = [
            ("Real-time Engine", st.session_state.realtime_enabled, "running"),
            ("AI Agents", st.session_state.ai_agents_running, "active"),
            ("Transformer Models", True, "loaded"),
            ("Security System", True, "protected"),
            ("Data Pipeline", True, "flowing"),
            ("Hardware Interface", len(st.session_state.connected_devices) > 0, "connected")
        ]
        
        for name, status, status_text in components:
            status_class = "status-running" if status else "status-stopped"
            st.markdown(f"""
            <div class="component-card">
                <span class="status-indicator {status_class}"></span>
                <strong>{name}</strong><br>
                <small>Status: {status_text}</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔄 Refresh All"):
            st.success("System refreshed!")
        
        if st.button("🧠 Run Transformer"):
            st.success("Transformer analysis started!")
        
        if st.button("📊 Generate Report"):
            st.success("Report generation initiated!")
    
    # Live EEG visualization
    st.subheader("🧠 Live Neural Signals")
    
    # Generate synthetic EEG data
    time_points = np.linspace(0, 4, 1000)  # 4 seconds
    channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2']
    
    fig_eeg = go.Figure()
    colors = px.colors.qualitative.Set3
    
    for i, channel in enumerate(channels):
        # Generate realistic EEG signal
        signal = (
            2 * np.sin(2 * np.pi * 10 * time_points) +  # Alpha (10 Hz)
            1 * np.sin(2 * np.pi * 20 * time_points) +  # Beta (20 Hz)
            0.5 * np.sin(2 * np.pi * 4 * time_points) + # Theta (4 Hz)
            0.3 * np.random.randn(len(time_points))     # Noise
        )
        
        # Offset channels vertically
        signal_offset = signal + i * 8
        
        fig_eeg.add_trace(go.Scatter(
            x=time_points,
            y=signal_offset,
            name=channel,
            line=dict(color=colors[i % len(colors)], width=1.5),
            hovertemplate=f'<b>{channel}</b><br>Time: %{{x:.2f}}s<br>Amplitude: %{{y:.1f}}μV'
        ))
    
    fig_eeg.update_layout(
        title="Real-time EEG Signals (10 channels)",
        xaxis_title="Time (seconds)",
        yaxis_title="Channels",
        height=400,
        yaxis=dict(
            tickmode='array',
            tickvals=[i * 8 for i in range(len(channels))],
            ticktext=channels
        )
    )
    st.plotly_chart(fig_eeg, use_container_width=True)

def show_data_playground():
    """Data playground with AI agents, pipeline builder, and model training"""
    st.header("🧪 Data Playground")
    
    # Sub-tabs for different playground features
    playground_tabs = st.tabs([
        "🤖 AI Agents", "🔧 Pipeline Builder", "🧠 Model Training", "📊 Data Explorer"
    ])
    
    with playground_tabs[0]:  # AI Agents
        show_ai_agents_section()
    
    with playground_tabs[1]:  # Pipeline Builder
        show_pipeline_builder_section()
    
    with playground_tabs[2]:  # Model Training
        show_model_training_section()
    
    with playground_tabs[3]:  # Data Explorer
        show_data_explorer_section()

def show_ai_agents_section():
    """AI agents management"""
    st.subheader("🤖 Autonomous AI Agents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Agent grid
        agents = [
            {
                "name": "Pipeline Optimizer",
                "type": "🔧 Optimizer",
                "status": "running" if st.session_state.ai_agents_running else "stopped",
                "confidence": 0.94,
                "decisions": 47,
                "description": "Continuously optimizes pipeline parameters for maximum performance",
                "recent_actions": [
                    "Reduced filter bandwidth by 2Hz → +3ms latency improvement",
                    "Adjusted buffer size → +12% throughput increase",
                    "Enabled adaptive thresholding → +1.2% accuracy boost"
                ]
            },
            {
                "name": "Anomaly Detective",
                "type": "🔍 Monitor", 
                "status": "running" if st.session_state.ai_agents_running else "stopped",
                "confidence": 0.89,
                "decisions": 23,
                "description": "Detects anomalies in signal quality and system behavior",
                "recent_actions": [
                    "Detected electrode impedance spike on Ch4",
                    "Identified 60Hz noise contamination",
                    "Flagged unusual pattern in motor cortex signals"
                ]
            },
            {
                "name": "Research Assistant",
                "type": "📚 Research",
                "status": "idle" if st.session_state.ai_agents_running else "stopped",
                "confidence": 0.97,
                "decisions": 12,
                "description": "Suggests research directions and experimental designs",
                "recent_actions": [
                    "Suggested P300 paradigm optimization",
                    "Recommended new feature extraction method",
                    "Proposed cross-subject validation strategy"
                ]
            }
        ]
        
        for agent in agents:
            with st.expander(f"{agent['type']} {agent['name']} - {agent['status'].upper()}", 
                            expanded=agent['status'] == 'running'):
                
                col_info, col_metrics, col_actions = st.columns([2, 1, 1])
                
                with col_info:
                    st.write(f"**Description:** {agent['description']}")
                    
                    if agent['status'] == 'running':
                        st.write("**Recent Actions:**")
                        for action in agent['recent_actions'][:2]:
                            st.write(f"• {action}")
                
                with col_metrics:
                    st.metric("Confidence", f"{agent['confidence']:.2%}")
                    st.metric("Decisions", agent['decisions'])
                
                with col_actions:
                    status_color = "🟢" if agent['status'] == 'running' else "🔴"
                    st.write(f"{status_color} **{agent['status'].title()}**")
                    
                    if agent['status'] != 'running':
                        if st.button(f"▶️ Start", key=f"start_{agent['name']}"):
                            st.success(f"Started {agent['name']}")
                    else:
                        if st.button(f"⏸️ Pause", key=f"pause_{agent['name']}"):
                            st.info(f"Paused {agent['name']}")
    
    with col2:
        st.subheader("🎛️ Agent Control")
        
        # Global controls
        if st.button("🚀 Start All Agents", disabled=st.session_state.ai_agents_running):
            st.session_state.ai_agents_running = True
            st.success("All agents activated!")
            st.rerun()
        
        if st.button("⏸️ Pause All Agents", disabled=not st.session_state.ai_agents_running):
            st.session_state.ai_agents_running = False
            st.info("All agents paused!")
            st.rerun()
        
        # Agent insights
        st.subheader("📊 Agent Insights")
        
        # Performance impact chart
        improvements = {
            'Latency': -8.5,
            'Throughput': +15.2,
            'Accuracy': +3.7,
            'Reliability': +12.1
        }
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(improvements.keys()),
            y=list(improvements.values()),
            text=[f"{v:+.1f}%" for v in improvements.values()],
            textposition='auto',
            marker_color=['#ff6b6b' if v < 0 else '#4ecdc4' for v in improvements.values()]
        ))
        
        fig.update_layout(
            title="AI Agent Performance Impact",
            yaxis_title="Improvement (%)",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

def show_pipeline_builder_section():
    """Interactive pipeline builder"""
    st.subheader("🔧 Visual Pipeline Builder")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Pipeline creation interface
        st.write("**Create New Pipeline:**")
        
        pipeline_name = st.text_input("Pipeline Name", "Advanced_BCI_Pipeline")
        
        # Task configuration
        col_task, col_signal = st.columns(2)
        with col_task:
            task_type = st.selectbox("Task Type", ["Motor Imagery", "P300 Speller", "SSVEP", "Hybrid BCI"])
        with col_signal:
            signal_type = st.selectbox("Signal Type", ["EEG", "ECoG", "fNIRS", "Multi-modal"])
        
        # Hardware configuration
        st.write("**Hardware Configuration:**")
        col_ch, col_sr, col_lat = st.columns(3)
        with col_ch:
            channels = st.slider("Channels", 8, 256, 64)
        with col_sr:
            sample_rate = st.selectbox("Sample Rate (Hz)", [250, 500, 1000, 2000])
        with col_lat:
            target_latency = st.slider("Target Latency (ms)", 10, 200, 50)
        
        # Pipeline stages
        st.write("**Pipeline Stages:**")
        
        # Preprocessing
        with st.expander("🔄 Preprocessing", expanded=True):
            preprocess_options = {
                "Bandpass Filter": {"enabled": True, "low": 1.0, "high": 40.0},
                "Notch Filter": {"enabled": True, "freq": 60},
                "Common Average Reference": {"enabled": True},
                "Artifact Removal": {"enabled": True, "method": "ICA"}
            }
            
            for option, params in preprocess_options.items():
                enabled = st.checkbox(option, value=params["enabled"])
                if enabled and option == "Bandpass Filter":
                    col_low, col_high = st.columns(2)
                    with col_low:
                        st.number_input("Low Freq (Hz)", value=params["low"])
                    with col_high:
                        st.number_input("High Freq (Hz)", value=params["high"])
        
        # Feature extraction
        with st.expander("🎯 Feature Extraction", expanded=True):
            feature_methods = st.multiselect(
                "Feature Methods",
                ["Bandpower", "CSP", "xDAWN", "Spectral Features", "Time-domain", "Wavelet"],
                default=["Bandpower", "CSP"]
            )
        
        # Model selection
        with st.expander("🧠 Model Selection", expanded=True):
            model_type = st.selectbox(
                "Model Type",
                ["EEGNet-Transformer", "CNN-LSTM", "SVM", "Random Forest", "Custom Transformer"]
            )
            
            if "Transformer" in model_type:
                col_d, col_h, col_l = st.columns(3)
                with col_d:
                    d_model = st.selectbox("Model Dimension", [128, 256, 512])
                with col_h:
                    n_heads = st.selectbox("Attention Heads", [4, 8, 16])
                with col_l:
                    n_layers = st.slider("Layers", 2, 12, 4)
        
        # Create pipeline button
        if st.button("🚀 Create Pipeline", type="primary"):
            pipeline_config = {
                "name": pipeline_name,
                "task_type": task_type,
                "signal_type": signal_type,
                "channels": channels,
                "sample_rate": sample_rate,
                "target_latency": target_latency,
                "preprocessing": preprocess_options,
                "features": feature_methods,
                "model": model_type,
                "created_at": datetime.now().isoformat()
            }
            
            st.session_state.active_pipelines.append(pipeline_config)
            st.success(f"✅ Pipeline '{pipeline_name}' created successfully!")
    
    with col2:
        st.subheader("📋 Active Pipelines")
        
        if st.session_state.active_pipelines:
            for i, pipeline in enumerate(st.session_state.active_pipelines):
                with st.container():
                    st.markdown(f"""
                    <div class="component-card">
                        <h4>{pipeline['name']}</h4>
                        <p><strong>Task:</strong> {pipeline['task_type']}</p>
                        <p><strong>Model:</strong> {pipeline.get('model', 'N/A')}</p>
                        <p><strong>Channels:</strong> {pipeline['channels']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_run, col_edit, col_del = st.columns(3)
                    with col_run:
                        if st.button("▶️ Run", key=f"run_{i}"):
                            st.success(f"Running {pipeline['name']}")
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_{i}"):
                            st.info("Edit mode activated")
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_{i}"):
                            st.session_state.active_pipelines.pop(i)
                            st.rerun()
        else:
            st.info("No pipelines created yet. Create your first pipeline!")
        
        # Pipeline templates
        st.subheader("📚 Templates")
        
        templates = {
            "🎯 Motor Imagery": "Optimized for left/right hand movement classification",
            "📝 P300 Speller": "Event-related potential detection for communication",
            "👁️ SSVEP": "Steady-state visual evoked potential classification",
            "🧠 Research": "General-purpose research pipeline"
        }
        
        for template, description in templates.items():
            if st.button(template):
                st.info(f"Loading template: {description}")

def show_model_training_section():
    """Enhanced model training with visualization"""
    st.subheader("🧠 Advanced Model Training")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Training configuration
        st.write("**Training Configuration:**")
        
        col_model, col_data = st.columns(2)
        with col_model:
            model_type = st.selectbox("Model Architecture", 
                                    ["EEGNet-Transformer", "Brain-to-Text", "Multi-Modal BCI"])
            optimizer = st.selectbox("Optimizer", ["AdamW", "Adam", "SGD"])
        with col_data:
            dataset = st.selectbox("Dataset", ["BCI Competition IV", "PhysioNet MI", "Custom Dataset"])
            validation_split = st.slider("Validation Split", 0.1, 0.3, 0.2)
        
        # Hyperparameters
        st.write("**Hyperparameters:**")
        col_lr, col_batch, col_epochs = st.columns(3)
        with col_lr:
            learning_rate = st.selectbox("Learning Rate", [0.0001, 0.001, 0.01])
        with col_batch:
            batch_size = st.selectbox("Batch Size", [16, 32, 64, 128])
        with col_epochs:
            epochs = st.slider("Epochs", 10, 200, 50)
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            use_scheduler = st.checkbox("Learning Rate Scheduler", value=True)
            early_stopping = st.checkbox("Early Stopping", value=True)
            data_augmentation = st.checkbox("Data Augmentation", value=True)
            mixed_precision = st.checkbox("Mixed Precision Training", value=True)
        
        # Model architecture visualization
        if model_type == "EEGNet-Transformer":
            st.markdown('<div class="model-viz">', unsafe_allow_html=True)
            st.write("**🏗️ Model Architecture Preview:**")
            
            # Create architecture diagram
            fig_arch = create_model_architecture_viz(model_type)
            st.plotly_chart(fig_arch, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Training button
        if st.button("🚀 Start Training", type="primary"):
            with st.spinner("Initializing training..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Training simulation with realistic timing
                total_steps = epochs
                for epoch in range(total_steps):
                    # Realistic training time (much faster)
                    time.sleep(0.05)  # 50ms per epoch simulation
                    
                    progress = (epoch + 1) / total_steps
                    progress_bar.progress(progress)
                    
                    # Simulate realistic metrics
                    train_loss = 0.8 * np.exp(-epoch * 0.1) + 0.1 + np.random.normal(0, 0.02)
                    val_acc = 85 * (1 - np.exp(-epoch * 0.15)) + np.random.normal(0, 1)
                    
                    status_text.text(f"Epoch {epoch+1}/{total_steps} - Loss: {train_loss:.4f}, Val Acc: {val_acc:.1f}%")
                
                st.success(f"✅ Training completed! Final accuracy: {val_acc:.1f}%")
                
                # Show training results
                show_training_results(epochs)
    
    with col2:
        st.subheader("📊 Training Monitor")
        
        # Resource usage
        st.write("**System Resources:**")
        col_cpu, col_gpu = st.columns(2)
        with col_cpu:
            st.metric("CPU Usage", "67%", "+5%")
        with col_gpu:
            st.metric("GPU Usage", "89%", "+12%")
        
        # Estimated time (fixed to be realistic)
        training_time_minutes = epochs * 0.1  # Much more realistic estimate
        st.metric("Est. Training Time", f"{training_time_minutes:.1f} min")
        
        # Model parameters
        if model_type == "EEGNet-Transformer":
            params = calculate_model_parameters(model_type)
            st.metric("Model Parameters", f"{params:,}")
            st.metric("Model Size", f"{params * 4 / (1024*1024):.1f} MB")
        
        # Training history
        st.write("**Recent Training Jobs:**")
        training_history = [
            {"model": "EEGNet-Transformer", "accuracy": "94.2%", "time": "2h ago"},
            {"model": "Brain-to-Text", "accuracy": "87.5%", "time": "1d ago"},
            {"model": "Multi-Modal", "accuracy": "91.8%", "time": "2d ago"}
        ]
        
        for job in training_history:
            st.markdown(f"""
            <div class="component-card" style="padding: 0.8rem;">
                <strong>{job['model']}</strong><br>
                <small>Accuracy: {job['accuracy']} • {job['time']}</small>
            </div>
            """, unsafe_allow_html=True)

def create_model_architecture_viz(model_type):
    """Create interactive model architecture visualization"""
    if model_type == "EEGNet-Transformer":
        # Create network graph for EEGNet-Transformer
        fig = go.Figure()
        
        # Define layers and connections
        layers = [
            {"name": "EEG Input\n(64, 1000)", "x": 0, "y": 2, "color": "#e3f2fd"},
            {"name": "Temporal Conv\n(16, 1000)", "x": 1, "y": 2, "color": "#ffecb3"},
            {"name": "Spatial Conv\n(32, 1)", "x": 2, "y": 2, "color": "#ffecb3"},
            {"name": "Separable Conv\n(64, 250)", "x": 3, "y": 2, "color": "#ffecb3"},
            {"name": "Projection\n(256, 250)", "x": 4, "y": 2, "color": "#e8f5e8"},
            {"name": "Pos Encoding", "x": 5, "y": 2, "color": "#e8f5e8"},
            {"name": "Multi-Head\nAttention", "x": 6, "y": 2, "color": "#fce4ec"},
            {"name": "Feed Forward", "x": 7, "y": 2, "color": "#fce4ec"},
            {"name": "Global Pool", "x": 8, "y": 2, "color": "#f3e5f5"},
            {"name": "Classification\n(2 classes)", "x": 9, "y": 2, "color": "#fff3e0"}
        ]
        
        # Add layer nodes
        for layer in layers:
            fig.add_trace(go.Scatter(
                x=[layer["x"]],
                y=[layer["y"]],
                mode='markers+text',
                text=[layer["name"]],
                textposition="middle center",
                marker=dict(size=60, color=layer["color"], 
                          line=dict(width=2, color="#333")),
                showlegend=False,
                hovertemplate=f"<b>{layer['name']}</b><extra></extra>"
            ))
        
        # Add connections
        for i in range(len(layers) - 1):
            fig.add_trace(go.Scatter(
                x=[layers[i]["x"], layers[i+1]["x"]],
                y=[layers[i]["y"], layers[i+1]["y"]],
                mode='lines',
                line=dict(color='#666', width=2),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        fig.update_layout(
            title="EEGNet-Transformer Architecture",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=250,
            margin=dict(l=0, r=0, t=30, b=0),
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig

def calculate_model_parameters(model_type):
    """Calculate approximate model parameters"""
    if model_type == "EEGNet-Transformer":
        # Approximate parameter count for EEGNet-Transformer
        cnn_params = 64 * 64 + 16 * 32 * 64 + 32 * 64  # Conv layers
        transformer_params = 256 * 256 * 8 * 4  # Transformer layers
        classifier_params = 256 * 2  # Classification head
        return cnn_params + transformer_params + classifier_params
    return 100000

def show_training_results(epochs):
    """Show training results with charts"""
    st.subheader("📈 Training Results")
    
    # Generate training curves
    train_losses = []
    val_losses = []
    val_accuracies = []
    
    for epoch in range(epochs):
        train_loss = 0.8 * np.exp(-epoch * 0.1) + 0.1 + np.random.normal(0, 0.02)
        val_loss = 0.9 * np.exp(-epoch * 0.08) + 0.15 + np.random.normal(0, 0.03)
        val_acc = 85 * (1 - np.exp(-epoch * 0.15)) + np.random.normal(0, 1)
        
        train_losses.append(max(0.05, train_loss))
        val_losses.append(max(0.1, val_loss))
        val_accuracies.append(max(50, min(95, val_acc)))
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Loss curves
        fig_loss = go.Figure()
        fig_loss.add_trace(go.Scatter(y=train_losses, name="Training Loss", line=dict(color='#ff6b6b')))
        fig_loss.add_trace(go.Scatter(y=val_losses, name="Validation Loss", line=dict(color='#4ecdc4')))
        fig_loss.update_layout(title="Training & Validation Loss", xaxis_title="Epoch", yaxis_title="Loss")
        st.plotly_chart(fig_loss, use_container_width=True)
    
    with col2:
        # Accuracy curve
        fig_acc = go.Figure()
        fig_acc.add_trace(go.Scatter(y=val_accuracies, name="Validation Accuracy", 
                                   line=dict(color='#45b7d1'), fill='tonexty'))
        fig_acc.update_layout(title="Validation Accuracy", xaxis_title="Epoch", yaxis_title="Accuracy (%)")
        st.plotly_chart(fig_acc, use_container_width=True)

def show_data_explorer_section():
    """Data exploration and analysis tools"""
    st.subheader("📊 Data Explorer")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Dataset overview
        st.write("**Available Datasets:**")
        
        datasets = [
            {"name": "BCI Competition IV", "samples": 2520, "subjects": 9, "type": "Motor Imagery"},
            {"name": "PhysioNet MI", "samples": 1440, "subjects": 109, "type": "Motor Imagery"},
            {"name": "P300 Speller", "samples": 5760, "subjects": 8, "type": "ERP"},
            {"name": "Custom Dataset", "samples": 3200, "subjects": 15, "type": "Mixed"}
        ]
        
        selected_dataset = st.selectbox("Select Dataset", [d["name"] for d in datasets])
        dataset_info = next(d for d in datasets if d["name"] == selected_dataset)
        
        # Dataset statistics
        col_samples, col_subjects, col_type = st.columns(3)
        with col_samples:
            st.metric("Samples", dataset_info["samples"])
        with col_subjects:
            st.metric("Subjects", dataset_info["subjects"])
        with col_type:
            st.metric("Type", dataset_info["type"])
        
        # Data visualization
        st.write("**Data Visualization:**")
        
        viz_type = st.selectbox("Visualization Type", 
                               ["Signal Overview", "Spectral Analysis", "Channel Correlation", "Classification Performance"])
        
        if viz_type == "Signal Overview":
            # Generate sample EEG data
            fig = create_sample_eeg_plot()
            st.plotly_chart(fig, use_container_width=True)
        
        elif viz_type == "Spectral Analysis":
            # Power spectral density
            freqs = np.linspace(1, 50, 100)
            psd = 1/freqs + np.random.normal(0, 0.1, len(freqs))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=freqs, y=psd, fill='tonexty', name='PSD'))
            fig.update_layout(title="Power Spectral Density", xaxis_title="Frequency (Hz)", yaxis_title="Power")
            st.plotly_chart(fig, use_container_width=True)
        
        elif viz_type == "Channel Correlation":
            # Correlation heatmap
            channels = 8
            corr_matrix = np.random.uniform(0.3, 1.0, (channels, channels))
            np.fill_diagonal(corr_matrix, 1.0)
            
            fig = go.Figure(data=go.Heatmap(z=corr_matrix, colorscale='RdBu'))
            fig.update_layout(title="Channel Cross-Correlation")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("**Data Quality Metrics:**")
        
        quality_metrics = {
            "Signal Quality": 94.2,
            "Noise Level": 12.3,
            "Artifact Rate": 3.1,
            "Missing Data": 0.8
        }
        
        for metric, value in quality_metrics.items():
            if metric in ["Signal Quality"]:
                color = "normal"
            elif metric in ["Noise Level", "Artifact Rate", "Missing Data"]:
                color = "inverse"
            else:
                color = "normal"
            
            if color == "normal":
                st.metric(metric, f"{value}%", "2.1%" if value > 90 else "-1.2%")
            else:
                st.metric(metric, f"{value}%", "-0.5%" if value < 15 else "+0.3%")
        
        # Data actions
        st.write("**Data Actions:**")
        
        if st.button("🔄 Preprocess Data"):
            st.success("Preprocessing initiated!")
        
        if st.button("📊 Generate Report"):
            st.success("Data report generated!")
        
        if st.button("📤 Export Dataset"):
            st.success("Export started!")

def create_sample_eeg_plot():
    """Create sample EEG plot for data explorer"""
    time_points = np.linspace(0, 2, 500)
    channels = ['C3', 'C4', 'Cz', 'Fz']
    
    fig = go.Figure()
    
    for i, channel in enumerate(channels):
        signal = np.sin(2 * np.pi * 10 * time_points) + 0.3 * np.random.randn(len(time_points))
        signal_offset = signal + i * 3
        
        fig.add_trace(go.Scatter(
            x=time_points,
            y=signal_offset,
            name=channel,
            line=dict(width=1.5)
        ))
    
    fig.update_layout(
        title="Sample EEG Signals",
        xaxis_title="Time (s)",
        yaxis_title="Channels",
        height=300
    )
    
    return fig

def show_neurosocial_feed():
    """NeuroSocial - Social platform for neuroscience collaboration"""
    st.header("🌐 NeuroSocial - Collaborative Neuroscience")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Main feed
        st.subheader("📡 Community Feed")
        
        # Create sample posts
        if not st.session_state.social_feed:
            st.session_state.social_feed = create_sample_social_posts()
        
        # Feed filters
        col_filter, col_sort = st.columns(2)
        with col_filter:
            feed_filter = st.selectbox("Filter by", ["All", "Peer Reviewed", "Trending", "Following"])
        with col_sort:
            sort_by = st.selectbox("Sort by", ["Recent", "Most Liked", "Most Shared", "Relevance"])
        
        # Display posts
        for post in st.session_state.social_feed:
            if feed_filter == "All" or feed_filter.lower() in post["tags"]:
                display_social_post(post)
    
    with col2:
        # Sidebar with trending topics and quick actions
        st.subheader("🔥 Trending Topics")
        
        trending = [
            {"topic": "#TransformerBCI", "posts": 47},
            {"topic": "#MotorImagery", "posts": 32},
            {"topic": "#OpenBCI", "posts": 28},
            {"topic": "#BrainToText", "posts": 21},
            {"topic": "#P300Speller", "posts": 18}
        ]
        
        for trend in trending:
            st.markdown(f"""
            <div class="component-card" style="padding: 0.8rem;">
                <strong>{trend['topic']}</strong><br>
                <small>{trend['posts']} posts</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick post
        st.subheader("✍️ Share Discovery")
        
        post_type = st.selectbox("Post Type", ["Research Update", "Dataset Share", "Code Release", "Question"])
        post_content = st.text_area("What's your latest discovery?", placeholder="Share your research insights...")
        
        col_attach, col_post = st.columns(2)
        with col_attach:
            if st.button("📎 Attach Data"):
                st.info("Data attachment ready!")
        with col_post:
            if st.button("📤 Post", type="primary"):
                if post_content:
                    new_post = {
                        "author": "You",
                        "content": post_content,
                        "type": post_type,
                        "likes": 0,
                        "shares": 0,
                        "comments": 0,
                        "timestamp": "Just now",
                        "tags": ["new"],
                        "verified": False
                    }
                    st.session_state.social_feed.insert(0, new_post)
                    st.success("Posted to NeuroSocial!")
                    st.rerun()
        
        # Community stats
        st.subheader("📊 Community Stats")
        
        stats = {
            "Active Researchers": 2847,
            "Shared Datasets": 156,
            "Code Repositories": 89,
            "Peer Reviews": 234
        }
        
        for stat, value in stats.items():
            st.metric(stat, f"{value:,}")

def create_sample_social_posts():
    """Create sample social media posts for NeuroSocial"""
    return [
        {
            "author": "Dr. Sarah Chen",
            "content": "Just achieved 94.7% accuracy on motor imagery classification using our new EEGNet-Transformer architecture! Dataset and code available for replication. #TransformerBCI #OpenScience",
            "type": "Research Update",
            "likes": 47,
            "shares": 23,
            "comments": 12,
            "timestamp": "2 hours ago",
            "tags": ["peer reviewed", "trending"],
            "verified": True,
            "data_attached": True
        },
        {
            "author": "Alex Rodriguez",
            "content": "New high-density EEG dataset from 50 subjects performing P300 speller tasks. IRB approved, anonymized, ready for research use. Link in comments. #P300 #OpenData",
            "type": "Dataset Share",
            "likes": 67,
            "shares": 34,
            "comments": 18,
            "timestamp": "5 hours ago",
            "tags": ["peer reviewed"],
            "verified": True,
            "data_attached": True
        },
        {
            "author": "Maria Santos",
            "content": "Has anyone successfully implemented real-time artifact removal for mobile EEG? Looking for collaboration on outdoor BCI experiments. #MobileBCI #Collaboration",
            "type": "Question",
            "likes": 15,
            "shares": 8,
            "comments": 24,
            "timestamp": "1 day ago",
            "tags": ["trending"],
            "verified": False,
            "data_attached": False
        },
        {
            "author": "BCI Research Lab",
            "content": "Open-source brain-to-text decoder achieving SOTA results on ALS patient data. Full codebase, models, and evaluation metrics now available. #BrainToText #ALS",
            "type": "Code Release",
            "likes": 89,
            "shares": 56,
            "comments": 31,
            "timestamp": "2 days ago",
            "tags": ["peer reviewed", "trending"],
            "verified": True,
            "data_attached": True
        }
    ]

def display_social_post(post):
    """Display a social media post"""
    # Determine post styling based on type
    if "peer reviewed" in post["tags"]:
        card_class = "social-card peer-reviewed"
        badge = "🔬 Peer Reviewed"
    elif "trending" in post["tags"]:
        card_class = "social-card trending"
        badge = "🔥 Trending"
    else:
        card_class = "social-card"
        badge = ""
    
    verification = "✅" if post["verified"] else ""
    data_icon = "📊" if post.get("data_attached", False) else ""
    
    st.markdown(f"""
    <div class="{card_class}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <strong>{post['author']} {verification}</strong>
            <small>{post['timestamp']}</small>
        </div>
        <p>{post['content']} {data_icon}</p>
        <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
            <small>❤️ {post['likes']}</small>
            <small>🔄 {post['shares']}</small>
            <small>💬 {post['comments']}</small>
            {f'<span style="background: #e3f2fd; padding: 0.2rem 0.5rem; border-radius: 10px; font-size: 0.8rem;">{badge}</span>' if badge else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Interaction buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("❤️ Like", key=f"like_{post['author']}_{post['timestamp']}"):
            st.success("Liked!")
    with col2:
        if st.button("🔄 Share", key=f"share_{post['author']}_{post['timestamp']}"):
            st.success("Shared!")
    with col3:
        if st.button("💬 Comment", key=f"comment_{post['author']}_{post['timestamp']}"):
            st.info("Comment added!")
    with col4:
        if post.get("data_attached", False):
            if st.button("📊 View Data", key=f"data_{post['author']}_{post['timestamp']}"):
                st.success("Opening dataset...")

def show_analytics_dashboard():
    """Enhanced analytics dashboard"""
    st.header("📊 Advanced Analytics Hub")
    
    # Analytics tabs
    analytics_tabs = st.tabs(["📈 Performance", "🧠 Neural Analysis", "🎯 Model Insights", "📊 Reports"])
    
    with analytics_tabs[0]:  # Performance Analytics
        show_performance_analytics()
    
    with analytics_tabs[1]:  # Neural Analysis
        show_neural_analysis()
    
    with analytics_tabs[2]:  # Model Insights
        show_model_insights()
    
    with analytics_tabs[3]:  # Reports
        show_reports_section()

def show_performance_analytics():
    """Show performance analytics"""
    # Performance metrics over time
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Avg Accuracy", "94.2%", "+2.1%")
    with col2:
        st.metric("Processing Speed", "247 Hz", "+12 Hz")
    with col3:
        st.metric("System Uptime", "99.8%", "+0.2%")
    with col4:
        st.metric("Data Processed", "15.3 GB", "+2.1 GB")
    
    # Performance trends
    st.subheader("📈 Performance Trends")
    
    # Generate trend data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='W')
    accuracy_trend = 85 + 10 * np.sin(np.arange(len(dates))/10) + np.random.normal(0, 2, len(dates))
    latency_trend = 50 + 10 * np.cos(np.arange(len(dates))/8) + np.random.normal(0, 3, len(dates))
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=dates, y=accuracy_trend, name="Accuracy (%)", line=dict(color='#4ecdc4')),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=dates, y=latency_trend, name="Latency (ms)", line=dict(color='#ff6b6b')),
        secondary_y=True,
    )
    
    fig.update_yaxes(title_text="Accuracy (%)", secondary_y=False)
    fig.update_yaxes(title_text="Latency (ms)", secondary_y=True)
    fig.update_layout(title="System Performance Over Time", height=400)
    
    st.plotly_chart(fig, use_container_width=True)

def show_neural_analysis():
    """Show neural signal analysis"""
    st.subheader("🧠 Neural Signal Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Frequency domain analysis
        st.write("**Power Spectral Density:**")
        
        freqs = np.linspace(1, 50, 100)
        # Realistic EEG PSD with alpha peak
        psd = (1/freqs**0.8 + 
               5 * np.exp(-((freqs - 10)**2) / 8) +  # Alpha peak
               2 * np.exp(-((freqs - 20)**2) / 20) +  # Beta
               np.random.normal(0, 0.1, len(freqs)))
        
        fig_psd = go.Figure()
        fig_psd.add_trace(go.Scatter(x=freqs, y=psd, fill='tonexty', name='PSD'))
        fig_psd.update_layout(
            xaxis_title="Frequency (Hz)",
            yaxis_title="Power (μV²/Hz)",
            height=300
        )
        st.plotly_chart(fig_psd, use_container_width=True)
    
    with col2:
        # Channel connectivity
        st.write("**Channel Connectivity:**")
        
        channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4']
        connectivity = np.random.uniform(0.3, 1.0, (len(channels), len(channels)))
        np.fill_diagonal(connectivity, 1.0)
        
        fig_conn = go.Figure(data=go.Heatmap(
            z=connectivity,
            x=channels,
            y=channels,
            colorscale='Viridis'
        ))
        fig_conn.update_layout(height=300)
        st.plotly_chart(fig_conn, use_container_width=True)

def show_model_insights():
    """Show model performance insights"""
    st.subheader("🎯 Model Performance Insights")
    
    # Model comparison
    models = ["EEGNet", "CNN-LSTM", "Transformer", "EEGNet-Transformer"]
    accuracies = [73.2, 75.8, 78.1, 82.4]
    latencies = [45, 67, 89, 52]
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Accuracy comparison
        fig_acc = go.Figure()
        fig_acc.add_trace(go.Bar(
            x=models,
            y=accuracies,
            text=[f"{acc}%" for acc in accuracies],
            textposition='auto',
            marker_color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        ))
        fig_acc.update_layout(title="Model Accuracy Comparison", yaxis_title="Accuracy (%)")
        st.plotly_chart(fig_acc, use_container_width=True)
    
    with col2:
        # Latency vs Accuracy scatter
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(
            x=latencies,
            y=accuracies,
            mode='markers+text',
            text=models,
            textposition="top center",
            marker=dict(size=15, color=['red', 'orange', 'green', 'blue'])
        ))
        fig_scatter.update_layout(
            title="Accuracy vs Latency Trade-off",
            xaxis_title="Latency (ms)",
            yaxis_title="Accuracy (%)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

def show_reports_section():
    """Show reports generation section"""
    st.subheader("📊 Automated Reports")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Report configuration
        st.write("**Generate Custom Report:**")
        
        report_type = st.selectbox("Report Type", 
                                 ["System Performance", "Model Evaluation", "Data Quality", "Security Audit"])
        date_range = st.date_input("Date Range", value=[datetime.now() - timedelta(days=7), datetime.now()])
        include_charts = st.checkbox("Include Charts", value=True)
        include_raw_data = st.checkbox("Include Raw Data", value=False)
        
        if st.button("📋 Generate Report", type="primary"):
            with st.spinner("Generating report..."):
                time.sleep(2)
                st.success("✅ Report generated successfully!")
                
                # Show sample report preview
                st.subheader("📄 Report Preview")
                st.markdown(f"""
                **{report_type} Report**
                
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                Period: {date_range[0]} to {date_range[1]}
                
                **Executive Summary:**
                - System performance maintained above 94% accuracy
                - Processing latency improved by 8ms over the period
                - No security incidents detected
                - 3 new models deployed successfully
                
                **Key Metrics:**
                - Total data processed: 15.3 GB
                - Average latency: 47.2ms
                - System uptime: 99.8%
                - Model accuracy: 94.2%
                
                **Recommendations:**
                - Consider upgrading to latest transformer architecture
                - Implement additional data augmentation techniques
                - Schedule preventive maintenance for next quarter
                """)
                
                if st.button("📥 Download Full Report"):
                    st.success("Report downloaded!")
    
    with col2:
        st.write("**Recent Reports:**")
        
        recent_reports = [
            {"name": "Weekly Performance", "date": "2024-01-15", "type": "Performance"},
            {"name": "Model Evaluation Q4", "date": "2024-01-10", "type": "Model"},
            {"name": "Security Audit", "date": "2024-01-08", "type": "Security"},
            {"name": "Data Quality Check", "date": "2024-01-05", "type": "Data"}
        ]
        
        for report in recent_reports:
            st.markdown(f"""
            <div class="component-card" style="padding: 0.8rem;">
                <strong>{report['name']}</strong><br>
                <small>{report['type']} • {report['date']}</small>
            </div>
            """, unsafe_allow_html=True)

def show_security_dashboard():
    """Enhanced security dashboard"""
    st.header("🔒 Security & Compliance Center")
    
    # Security overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Security Score", "98/100", "+2")
    with col2:
        st.metric("Active Threats", "0", "-1")
    with col3:
        st.metric("Compliance", "100%", "0%")
    with col4:
        st.metric("Last Audit", "2 days ago", "")
    
    # Security details in tabs
    security_tabs = st.tabs(["🛡️ Threats", "📋 Compliance", "🔐 Access", "📜 Audit Log"])
    
    with security_tabs[0]:  # Threat Detection
        st.subheader("🛡️ Threat Detection & Prevention")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Security Status:**")
            
            security_items = [
                ("Firewall", "Active", "🟢"),
                ("Intrusion Detection", "Monitoring", "🟢"),
                ("Data Encryption", "AES-256", "🟢"),
                ("Access Control", "RBAC Active", "🟢"),
                ("VPN Status", "Connected", "🟢"),
                ("Backup Status", "Automated", "🟢")
            ]
            
            for item, status, indicator in security_items:
                st.markdown(f"{indicator} **{item}**: {status}")
        
        with col2:
            st.write("**Recent Security Events:**")
            
            events = [
                {"type": "Login", "user": "admin", "status": "Success", "time": "5 min ago"},
                {"type": "Data Access", "user": "researcher1", "status": "Authorized", "time": "15 min ago"},
                {"type": "System Scan", "user": "system", "status": "Clean", "time": "1 hour ago"},
                {"type": "Backup", "user": "system", "status": "Complete", "time": "2 hours ago"}
            ]
            
            for event in events:
                status_color = "🟢" if event["status"] in ["Success", "Authorized", "Clean", "Complete"] else "🔴"
                st.markdown(f"{status_color} **{event['type']}** by {event['user']} - {event['time']}")
    
    with security_tabs[1]:  # Compliance
        st.subheader("📋 Compliance Dashboard")
        
        # Compliance standards
        compliance_standards = [
            {"name": "HIPAA", "status": "Compliant", "score": 100, "last_check": "2024-01-10"},
            {"name": "GDPR", "status": "Compliant", "score": 98, "last_check": "2024-01-08"},
            {"name": "ISO 27001", "status": "In Progress", "score": 85, "last_check": "2024-01-05"},
            {"name": "FDA 21 CFR Part 11", "status": "Compliant", "score": 95, "last_check": "2024-01-03"}
        ]
        
        for standard in compliance_standards:
            with st.expander(f"{standard['name']} - {standard['status']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Compliance Score", f"{standard['score']}/100")
                with col2:
                    st.write(f"**Status:** {standard['status']}")
                with col3:
                    st.write(f"**Last Check:** {standard['last_check']}")
                
                # Progress bar
                progress = standard['score'] / 100
                st.progress(progress)
                
                if standard['score'] < 100:
                    st.warning(f"Action required to achieve full {standard['name']} compliance")
                else:
                    st.success(f"Fully compliant with {standard['name']} standards")
    
    with security_tabs[2]:  # Access Control
        st.subheader("🔐 Access Control Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Active Users:**")
            
            users = [
                {"name": "Dr. Jane Smith", "role": "Administrator", "last_login": "5 min ago", "status": "Online"},
                {"name": "Alex Johnson", "role": "Researcher", "last_login": "2 hours ago", "status": "Offline"},
                {"name": "Maria Garcia", "role": "Clinician", "last_login": "1 day ago", "status": "Away"},
                {"name": "David Chen", "role": "Engineer", "last_login": "3 days ago", "status": "Offline"}
            ]
            
            for user in users:
                status_indicator = "🟢" if user["status"] == "Online" else "🟡" if user["status"] == "Away" else "🔴"
                st.markdown(f"""
                <div class="component-card" style="padding: 0.8rem;">
                    {status_indicator} <strong>{user['name']}</strong><br>
                    <small>{user['role']} • Last login: {user['last_login']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.write("**Permission Matrix:**")
            
            permissions = pd.DataFrame({
                'Role': ['Administrator', 'Researcher', 'Clinician', 'Engineer'],
                'Data Access': ['Full', 'Read/Write', 'Read Only', 'Limited'],
                'System Config': ['Yes', 'No', 'No', 'Yes'],
                'User Management': ['Yes', 'No', 'No', 'No']
            })
            
            st.dataframe(permissions, use_container_width=True)
    
    with security_tabs[3]:  # Audit Log
        st.subheader("📜 Security Audit Log")
        
        # Audit log table
        audit_data = {
            'Timestamp': [
                datetime.now() - timedelta(minutes=5),
                datetime.now() - timedelta(minutes=15),
                datetime.now() - timedelta(hours=1),
                datetime.now() - timedelta(hours=2),
                datetime.now() - timedelta(hours=4)
            ],
            'User': ['admin', 'researcher1', 'system', 'clinician2', 'engineer1'],
            'Action': [
                'User login',
                'Data export',
                'Security scan',
                'Patient data access',
                'System configuration change'
            ],
            'Resource': ['Auth System', 'Dataset_001', 'Security Module', 'Patient_DB', 'System Config'],
            'Status': ['Success', 'Success', 'Complete', 'Authorized', 'Success'],
            'IP Address': ['192.168.1.100', '192.168.1.101', 'localhost', '192.168.1.102', '192.168.1.103']
        }
        
        audit_df = pd.DataFrame(audit_data)
        st.dataframe(audit_df, use_container_width=True)
        
        # Export audit log
        if st.button("📥 Export Audit Log"):
            st.success("Audit log exported successfully!")

def show_settings_dashboard():
    """Comprehensive settings dashboard"""
    st.header("⚙️ System Settings & Configuration")
    
    settings_tabs = st.tabs(["🎨 Interface", "🔧 System", "👤 User", "🔌 Integrations", "🌐 Network"])
    
    with settings_tabs[0]:  # Interface Settings
        show_interface_settings()
    
    with settings_tabs[1]:  # System Settings
        show_system_settings()
    
    with settings_tabs[2]:  # User Settings
        show_user_settings()
    
    with settings_tabs[3]:  # Integration Settings
        show_integration_settings()
    
    with settings_tabs[4]:  # Network Settings
        show_network_settings()

def show_interface_settings():
    """Interface customization settings"""
    st.subheader("🎨 Interface Customization")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Theme settings
        st.write("**Appearance:**")
        
        theme = st.selectbox("Theme", ["Dark", "Light", "Auto", "High Contrast"])
        color_scheme = st.selectbox("Color Scheme", ["Blue", "Green", "Purple", "Orange"])
        sidebar_style = st.selectbox("Sidebar Style", ["Fixed", "Collapsible", "Overlay"])
        
        # Layout settings
        st.write("**Layout:**")
        
        density = st.selectbox("Display Density", ["Comfortable", "Compact", "Spacious"])
        show_animations = st.checkbox("Enable Animations", value=True)
        show_tooltips = st.checkbox("Show Tooltips", value=True)
    
    with col2:
        # Dashboard customization
        st.write("**Dashboard:**")
        
        default_tab = st.selectbox("Default Tab", ["Monitor", "Analytics", "Data Playground"])
        refresh_rate = st.slider("Auto-refresh Rate (seconds)", 5, 60, 30)
        max_charts = st.slider("Max Charts per Page", 4, 12, 8)
        
        # Notification settings
        st.write("**Notifications:**")
        
        enable_notifications = st.checkbox("Enable Notifications", value=True)
        notification_sound = st.checkbox("Notification Sound", value=False)
        toast_duration = st.slider("Toast Duration (seconds)", 2, 10, 5)

def show_system_settings():
    """System configuration settings"""
    st.subheader("🔧 System Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Performance settings
        st.write("**Performance:**")
        
        max_cpu_usage = st.slider("Max CPU Usage (%)", 50, 100, 80)
        memory_limit = st.slider("Memory Limit (GB)", 4, 64, 16)
        gpu_acceleration = st.checkbox("GPU Acceleration", value=True)
        
        # Processing settings
        st.write("**Processing:**")
        
        buffer_size = st.selectbox("Buffer Size", ["512 samples", "1024 samples", "2048 samples"])
        processing_threads = st.slider("Processing Threads", 1, 16, 4)
        batch_processing = st.checkbox("Batch Processing", value=True)
    
    with col2:
        # Storage settings
        st.write("**Storage:**")
        
        data_retention = st.slider("Data Retention (days)", 7, 365, 90)
        auto_backup = st.checkbox("Auto Backup", value=True)
        compression = st.checkbox("Data Compression", value=True)
        
        # Logging settings
        st.write("**Logging:**")
        
        log_level = st.selectbox("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"])
        log_rotation = st.selectbox("Log Rotation", ["Daily", "Weekly", "Monthly"])
        max_log_size = st.slider("Max Log Size (MB)", 10, 1000, 100)

def show_user_settings():
    """User preferences and profile settings"""
    st.subheader("👤 User Profile & Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Profile information
        st.write("**Profile:**")
        
        full_name = st.text_input("Full Name", value="Dr. Jane Smith")
        email = st.text_input("Email", value="jane.smith@neuros.ai")
        role = st.selectbox("Role", ["Administrator", "Researcher", "Clinician", "Engineer"])
        department = st.text_input("Department", value="Neuroscience Research")
        
        # Preferences
        st.write("**Preferences:**")
        
        timezone = st.selectbox("Timezone", ["UTC", "EST", "PST", "CET", "JST"])
        language = st.selectbox("Language", ["English", "Spanish", "French", "German", "Chinese"])
        date_format = st.selectbox("Date Format", ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"])
    
    with col2:
        # Notification preferences
        st.write("**Notifications:**")
        
        email_alerts = st.checkbox("Email Alerts", value=True)
        sms_alerts = st.checkbox("SMS Alerts", value=False)
        push_notifications = st.checkbox("Push Notifications", value=True)
        
        # Alert thresholds
        st.write("**Alert Thresholds:**")
        
        accuracy_threshold = st.slider("Accuracy Alert (%)", 70, 99, 85)
        latency_threshold = st.slider("Latency Alert (ms)", 50, 200, 100)
        error_threshold = st.slider("Error Rate Alert (%)", 1, 10, 5)

def show_integration_settings():
    """External integrations and API settings"""
    st.subheader("🔌 External Integrations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # AI/ML Integrations
        st.write("**AI/ML Services:**")
        
        openai_enabled = st.checkbox("OpenAI Integration", value=False)
        if openai_enabled:
            openai_api_key = st.text_input("OpenAI API Key", type="password")
            openai_model = st.selectbox("Default Model", ["gpt-4", "gpt-3.5-turbo"])
        
        huggingface_enabled = st.checkbox("Hugging Face Integration", value=True)
        if huggingface_enabled:
            hf_token = st.text_input("HF Token", type="password")
        
        # Cloud services
        st.write("**Cloud Services:**")
        
        aws_enabled = st.checkbox("AWS Integration", value=False)
        azure_enabled = st.checkbox("Azure Integration", value=False)
        gcp_enabled = st.checkbox("Google Cloud Integration", value=False)
    
    with col2:
        # Communication integrations
        st.write("**Communication:**")
        
        slack_enabled = st.checkbox("Slack Integration", value=True)
        if slack_enabled:
            slack_webhook = st.text_input("Slack Webhook URL", type="password")
            slack_channel = st.text_input("Default Channel", value="#neuros-alerts")
        
        teams_enabled = st.checkbox("Microsoft Teams", value=False)
        discord_enabled = st.checkbox("Discord Integration", value=False)
        
        # Monitoring integrations
        st.write("**Monitoring:**")
        
        wandb_enabled = st.checkbox("Weights & Biases", value=True)
        if wandb_enabled:
            wandb_project = st.text_input("W&B Project", value="neuros-monitoring")
        
        tensorboard_enabled = st.checkbox("TensorBoard", value=True)

def show_network_settings():
    """Network and connectivity settings"""
    st.subheader("🌐 Network Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Network settings
        st.write("**Network:**")
        
        api_host = st.text_input("API Host", value="0.0.0.0")
        api_port = st.number_input("API Port", value=8000, min_value=1000, max_value=65535)
        max_connections = st.slider("Max Connections", 10, 1000, 100)
        
        # Security settings
        st.write("**Security:**")
        
        enable_https = st.checkbox("Enable HTTPS", value=True)
        require_auth = st.checkbox("Require Authentication", value=True)
        session_timeout = st.slider("Session Timeout (minutes)", 15, 480, 60)
    
    with col2:
        # Proxy settings
        st.write("**Proxy:**")
        
        use_proxy = st.checkbox("Use Proxy", value=False)
        if use_proxy:
            proxy_host = st.text_input("Proxy Host")
            proxy_port = st.number_input("Proxy Port", value=8080)
            proxy_auth = st.checkbox("Proxy Authentication")
        
        # CORS settings
        st.write("**CORS:**")
        
        enable_cors = st.checkbox("Enable CORS", value=True)
        allowed_origins = st.text_area("Allowed Origins", value="https://localhost:3000\nhttps://neuros.ai")

def show_connections_dashboard():
    """Enhanced connections and collaboration dashboard"""
    st.header("🔗 Connections & Collaboration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Active connections
        st.subheader("👥 Research Network")
        
        # Connection tabs
        conn_tabs = st.tabs(["🌐 Active", "📞 Meetings", "📁 Shared", "🔍 Discover"])
        
        with conn_tabs[0]:  # Active Connections
            connections = [
                {
                    "name": "Dr. Sarah Chen",
                    "institution": "Stanford Neuroscience",
                    "expertise": "Motor Imagery BCI",
                    "status": "online",
                    "last_interaction": "2 hours ago",
                    "shared_projects": 3,
                    "avatar": "👩‍⚕️"
                },
                {
                    "name": "Alex Rodriguez",
                    "institution": "MIT CSAIL",
                    "expertise": "Neural Decoders",
                    "status": "away",
                    "last_interaction": "1 day ago",
                    "shared_projects": 1,
                    "avatar": "👨‍💻"
                },
                {
                    "name": "BCI Research Lab",
                    "institution": "University of California",
                    "expertise": "Multi-modal BCI",
                    "status": "online",
                    "last_interaction": "5 minutes ago",
                    "shared_projects": 2,
                    "avatar": "🏛️"
                }
            ]
            
            for conn in connections:
                status_color = "🟢" if conn["status"] == "online" else "🟡" if conn["status"] == "away" else "🔴"
                
                with st.expander(f"{conn['avatar']} {conn['name']} - {conn['institution']}", expanded=False):
                    col_info, col_actions = st.columns([2, 1])
                    
                    with col_info:
                        st.write(f"**Expertise:** {conn['expertise']}")
                        st.write(f"**Status:** {status_color} {conn['status']}")
                        st.write(f"**Last interaction:** {conn['last_interaction']}")
                        st.write(f"**Shared projects:** {conn['shared_projects']}")
                    
                    with col_actions:
                        if st.button("💬 Message", key=f"msg_{conn['name']}"):
                            st.success(f"Message sent to {conn['name']}")
                        if st.button("📁 Share Data", key=f"share_{conn['name']}"):
                            st.success("Data sharing initiated")
                        if st.button("🎥 Video Call", key=f"call_{conn['name']}"):
                            st.success("Video call started")
        
        with conn_tabs[1]:  # Meetings
            st.write("**Upcoming Meetings:**")
            
            meetings = [
                {"title": "BCI Collaboration Review", "time": "Today 2:00 PM", "attendees": 4},
                {"title": "Data Sharing Protocol", "time": "Tomorrow 10:00 AM", "attendees": 6},
                {"title": "Weekly Research Sync", "time": "Friday 9:00 AM", "attendees": 8}
            ]
            
            for meeting in meetings:
                st.markdown(f"""
                <div class="component-card" style="padding: 1rem;">
                    <strong>{meeting['title']}</strong><br>
                    <small>📅 {meeting['time']} • 👥 {meeting['attendees']} attendees</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Join Meeting", key=f"join_{meeting['title']}"):
                    st.success("Joining meeting...")
        
        with conn_tabs[2]:  # Shared Resources
            st.write("**Shared Resources:**")
            
            resources = [
                {"name": "Motor Imagery Dataset v2.1", "type": "Dataset", "size": "2.3 GB", "shared_by": "Dr. Sarah Chen"},
                {"name": "EEGNet-Transformer Code", "type": "Code", "size": "45 MB", "shared_by": "Alex Rodriguez"},
                {"name": "P300 Analysis Pipeline", "type": "Pipeline", "size": "12 MB", "shared_by": "BCI Research Lab"}
            ]
            
            for resource in resources:
                with st.container():
                    col_info, col_action = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"📊 **{resource['name']}**")
                        st.caption(f"{resource['type']} • {resource['size']} • Shared by {resource['shared_by']}")
                    
                    with col_action:
                        if st.button("📥 Download", key=f"dl_{resource['name']}"):
                            st.success("Download started!")
        
        with conn_tabs[3]:  # Discover
            st.write("**Discover Researchers:**")
            
            search_query = st.text_input("Search by expertise, institution, or research area")
            
            if search_query:
                st.write("**Search Results:**")
                
                # Sample search results
                results = [
                    {"name": "Dr. Emily Watson", "institution": "Harvard Medical", "match": "95%"},
                    {"name": "Prof. Michael Zhang", "institution": "UC Berkeley", "match": "87%"},
                    {"name": "Dr. Lisa Anderson", "institution": "Johns Hopkins", "match": "82%"}
                ]
                
                for result in results:
                    col_info, col_connect = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"**{result['name']}** - {result['institution']}")
                        st.caption(f"Match: {result['match']}")
                    
                    with col_connect:
                        if st.button("🤝 Connect", key=f"connect_{result['name']}"):
                            st.success("Connection request sent!")
    
    with col2:
        # Collaboration tools
        st.subheader("🛠️ Collaboration Tools")
        
        # Quick actions
        st.write("**Quick Actions:**")
        
        if st.button("🎥 Start Video Conference"):
            st.success("Video conference started!")
        
        if st.button("📺 Share Screen"):
            st.success("Screen sharing initiated!")
        
        if st.button("📝 Create Shared Notebook"):
            st.success("Shared notebook created!")
        
        # Activity feed
        st.write("**Recent Activity:**")
        
        activities = [
            {"user": "Dr. Sarah Chen", "action": "shared new dataset", "time": "5 min ago"},
            {"user": "Alex Rodriguez", "action": "updated shared code", "time": "1 hour ago"},
            {"user": "BCI Research Lab", "action": "invited to meeting", "time": "2 hours ago"}
        ]
        
        for activity in activities:
            st.markdown(f"""
            <div style="padding: 0.5rem; border-left: 3px solid #4ecdc4; margin: 0.5rem 0;">
                <strong>{activity['user']}</strong> {activity['action']}<br>
                <small>{activity['time']}</small>
            </div>
            """, unsafe_allow_html=True)

def show_hardware_dashboard():
    """Enhanced hardware management dashboard"""
    st.header("🛠️ Hardware Management Center")
    
    # Hardware overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Connected Devices", len(st.session_state.connected_devices))
    with col2:
        st.metric("Active Streams", "2")
    with col3:
        st.metric("Signal Quality", "94.2%")
    with col4:
        st.metric("Impedance Status", "Good")
    
    # Hardware tabs
    hardware_tabs = st.tabs(["🔌 Devices", "📊 Monitoring", "⚙️ Configuration", "🔧 Diagnostics"])
    
    with hardware_tabs[0]:  # Device Management
        show_device_management()
    
    with hardware_tabs[1]:  # Signal Monitoring
        show_signal_monitoring()
    
    with hardware_tabs[2]:  # Device Configuration
        show_device_configuration()
    
    with hardware_tabs[3]:  # Diagnostics
        show_hardware_diagnostics()

def show_device_management():
    """Device management interface"""
    st.subheader("🔌 Device Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Device discovery
        if st.button("🔍 Scan for Devices"):
            with st.spinner("Scanning for BCI devices..."):
                time.sleep(2)
                st.success("Scan completed! Found 3 devices.")
        
        # Device list
        devices = [
            {
                "name": "OpenBCI Cyton",
                "id": "OBC_001",
                "type": "EEG",
                "channels": 8,
                "sample_rate": 250,
                "status": "connected",
                "battery": 85,
                "signal_quality": 92
            },
            {
                "name": "Emotiv EPOC",
                "id": "EMT_001", 
                "type": "EEG",
                "channels": 14,
                "sample_rate": 256,
                "status": "available",
                "battery": 67,
                "signal_quality": 88
            },
            {
                "name": "g.tec Nautilus",
                "id": "GTC_001",
                "type": "EEG",
                "channels": 32,
                "sample_rate": 500,
                "status": "connected",
                "battery": 92,
                "signal_quality": 96
            }
        ]
        
        for device in devices:
            status_color = "🟢" if device["status"] == "connected" else "🟡"
            
            with st.expander(f"{status_color} {device['name']} ({device['id']})", 
                            expanded=device["status"] == "connected"):
                
                col_info, col_metrics, col_actions = st.columns([2, 1, 1])
                
                with col_info:
                    st.write(f"**Type:** {device['type']}")
                    st.write(f"**Channels:** {device['channels']}")
                    st.write(f"**Sample Rate:** {device['sample_rate']} Hz")
                    st.write(f"**Status:** {device['status']}")
                
                with col_metrics:
                    st.metric("Battery", f"{device['battery']}%")
                    st.metric("Signal Quality", f"{device['signal_quality']}%")
                
                with col_actions:
                    if device["status"] == "available":
                        if st.button("🔗 Connect", key=f"connect_{device['id']}"):
                            st.success(f"Connected to {device['name']}")
                    else:
                        if st.button("▶️ Start Stream", key=f"stream_{device['id']}"):
                            st.success("Data streaming started!")
                        if st.button("⚙️ Configure", key=f"config_{device['id']}"):
                            st.info("Opening configuration...")
    
    with col2:
        st.subheader("📊 Device Status")
        
        # Overall status
        st.write("**System Status:**")
        
        system_status = [
            ("Streaming", "Active", "🟢"),
            ("Data Quality", "Excellent", "🟢"),
            ("Impedance", "Good", "🟢"),
            ("Connectivity", "Stable", "🟢")
        ]
        
        for item, status, indicator in system_status:
            st.markdown(f"{indicator} **{item}:** {status}")
        
        # Quick device actions
        st.write("**Quick Actions:**")
        
        if st.button("🔄 Refresh All"):
            st.success("All devices refreshed!")
        
        if st.button("⏸️ Stop All Streams"):
            st.info("All streams stopped!")
        
        if st.button("📊 Check Impedance"):
            st.success("Impedance check completed!")

def show_signal_monitoring():
    """Real-time signal monitoring"""
    st.subheader("📊 Signal Monitoring")
    
    # Live signal display
    fig_signals = create_live_signal_display()
    st.plotly_chart(fig_signals, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Signal quality metrics
        st.write("**Signal Quality Metrics:**")
        
        channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4']
        quality_scores = np.random.uniform(85, 98, len(channels))
        
        for i, (channel, quality) in enumerate(zip(channels, quality_scores)):
            color = "🟢" if quality > 90 else "🟡" if quality > 80 else "🔴"
            st.markdown(f"{color} **{channel}:** {quality:.1f}%")
        
        # Impedance status
        st.write("**Impedance Status:**")
        
        impedances = np.random.uniform(2, 15, len(channels))
        for channel, impedance in zip(channels, impedances):
            color = "🟢" if impedance < 5 else "🟡" if impedance < 10 else "🔴"
            st.markdown(f"{color} **{channel}:** {impedance:.1f} kΩ")
    
    with col2:
        # Frequency analysis
        st.write("**Frequency Band Power:**")
        
        bands = {
            'Delta (1-4 Hz)': np.random.uniform(20, 40),
            'Theta (4-8 Hz)': np.random.uniform(15, 30),
            'Alpha (8-13 Hz)': np.random.uniform(25, 45),
            'Beta (13-30 Hz)': np.random.uniform(10, 25),
            'Gamma (30-50 Hz)': np.random.uniform(5, 15)
        }
        
        for band, power in bands.items():
            st.metric(band, f"{power:.1f}%")
        
        # Alert thresholds
        st.write("**Alert Thresholds:**")
        
        quality_threshold = st.slider("Min Signal Quality (%)", 70, 95, 85)
        impedance_threshold = st.slider("Max Impedance (kΩ)", 5, 20, 10)
        
        if st.button("🚨 Set Alerts"):
            st.success("Alert thresholds updated!")
def create_live_signal_display():
    """Create live signal display"""
    time_points = np.linspace(0, 4, 1000)
    channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4']
    
    fig = go.Figure()
    colors = px.colors.qualitative.Set3
    
    for i, channel in enumerate(channels):
        # Generate realistic EEG signal
        signal = (
            3 * np.sin(2 * np.pi * 10 * time_points) +  # Alpha
            1.5 * np.sin(2 * np.pi * 20 * time_points) +  # Beta
            0.8 * np.sin(2 * np.pi * 4 * time_points) +  # Theta
            0.4 * np.random.randn(len(time_points))     # Noise
        )
        
        # Offset channels
        signal_offset = signal + i * 12
        
        fig.add_trace(go.Scatter(
            x=time_points,
            y=signal_offset,
            name=channel,
            line=dict(color=colors[i % len(colors)], width=1.5),
            hovertemplate=f'<b>{channel}</b><br>Time: %{{x:.2f}}s<br>Amplitude: %{{y:.1f}}μV'
        ))
    
    fig.update_layout(
        title="Real-time EEG Signals",
        xaxis_title="Time (seconds)",
        yaxis_title="Channels",
        height=400,
        yaxis=dict(
            tickmode='array',
            tickvals=[i * 12 for i in range(len(channels))],
            ticktext=channels
        )
    )
    
    return fig

def show_device_configuration():
    """Device configuration interface"""
    st.subheader("⚙️ Device Configuration")
    
    # Select device to configure
    device_to_config = st.selectbox("Select Device", ["OpenBCI Cyton", "Emotiv EPOC", "g.tec Nautilus"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Signal acquisition settings
        st.write("**Signal Acquisition:**")
        
        sample_rate = st.selectbox("Sample Rate (Hz)", [250, 500, 1000, 2000])
        gain = st.slider("Gain", 1, 24, 12)
        highpass_filter = st.number_input("Highpass Filter (Hz)", 0.1, 50.0, 1.0)
        lowpass_filter = st.number_input("Lowpass Filter (Hz)", 1.0, 500.0, 50.0)
        
        # Channel configuration
        st.write("**Channel Configuration:**")
        
        if device_to_config == "OpenBCI Cyton":
            channels = [f"Channel {i+1}" for i in range(8)]
        elif device_to_config == "Emotiv EPOC":
            channels = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']
        else:
            channels = [f"Channel {i+1}" for i in range(32)]
        
        enabled_channels = st.multiselect("Enabled Channels", channels, default=channels[:8])
    
    with col2:
        # Advanced settings
        st.write("**Advanced Settings:**")
        
        impedance_check = st.checkbox("Auto Impedance Check", value=True)
        bias_voltage = st.slider("Bias Voltage (V)", -2.0, 2.0, 0.0)
        notch_filter = st.selectbox("Notch Filter", ["Off", "50 Hz", "60 Hz"])
        
        # Streaming settings
        st.write("**Streaming:**")
        
        buffer_size = st.selectbox("Buffer Size", ["256", "512", "1024", "2048"])
        compression = st.checkbox("Data Compression", value=False)
        
        # Apply configuration
        if st.button("💾 Apply Configuration", type="primary"):
            st.success(f"Configuration applied to {device_to_config}!")
        
        if st.button("🔄 Reset to Default"):
            st.info("Configuration reset to defaults!")

def show_hardware_diagnostics():
    """Hardware diagnostics and testing"""
    st.subheader("🔧 Hardware Diagnostics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # System diagnostics
        st.write("**System Diagnostics:**")
        
        if st.button("🔍 Run Full Diagnostic"):
            with st.spinner("Running comprehensive diagnostic..."):
                time.sleep(3)
                
                diagnostic_results = {
                    "Hardware Detection": "✅ Pass",
                    "Signal Quality": "✅ Pass", 
                    "Impedance Check": "⚠️ Warning (Ch4 high)",
                    "Connectivity": "✅ Pass",
                    "Data Integrity": "✅ Pass",
                    "Timing Accuracy": "✅ Pass"
                }
                
                st.write("**Diagnostic Results:**")
                for test, result in diagnostic_results.items():
                    st.write(f"{result} {test}")
                
                st.success("Diagnostic completed!")
        
        # Individual tests
        st.write("**Individual Tests:**")
        
        test_buttons = [
            ("🔌 Connection Test", "Testing device connectivity..."),
            ("📊 Signal Test", "Testing signal acquisition..."),
            ("⚡ Impedance Test", "Checking electrode impedances..."),
            ("🕐 Timing Test", "Verifying sample timing...")
        ]
        
        for button_text, loading_text in test_buttons:
            if st.button(button_text):
                with st.spinner(loading_text):
                    time.sleep(1)
                    st.success("Test completed successfully!")
    
    with col2:
        # Hardware information
        st.write("**Hardware Information:**")
        
        hw_info = {
            "CPU Usage": f"{st.session_state.system_health['cpu_usage']:.1f}%",
            "Memory Usage": f"{st.session_state.system_health['memory_usage']:.1f}%",
            "GPU Usage": f"{st.session_state.system_health['gpu_usage']:.1f}%",
            "Disk Usage": f"{st.session_state.system_health['disk_usage']:.1f}%",
            "Temperature": "62°C",
            "Power Draw": "145W"
        }
        
        for metric, value in hw_info.items():
            st.metric(metric, value)
        
        # System health chart
        st.write("**System Health Trend:**")
        
        time_range = pd.date_range(start=datetime.now() - timedelta(hours=1), 
                                 end=datetime.now(), freq='5min')
        cpu_trend = st.session_state.system_health['cpu_usage'] + np.random.normal(0, 5, len(time_range))
        
        fig_health = go.Figure()
        fig_health.add_trace(go.Scatter(
            x=time_range,
            y=cpu_trend,
            fill='tonexty',
            name='CPU Usage (%)',
            line=dict(color='#ff6b6b')
        ))
        
        fig_health.update_layout(
            title="CPU Usage Trend",
            xaxis_title="Time",
            yaxis_title="Usage (%)",
            height=250
        )
        
        st.plotly_chart(fig_health, use_container_width=True)

# Save settings function
def save_all_settings():
    """Save all settings to file"""
    settings_data = {
        'user_settings': st.session_state.user_settings,
        'system_health': st.session_state.system_health,
        'connected_devices': st.session_state.connected_devices,
        'active_pipelines': st.session_state.active_pipelines,
        'timestamp': datetime.now().isoformat()
    }
    
    # In a real application, this would save to a database
    settings_file = Path("neuros_settings.json")
    with open(settings_file, 'w') as f:
        json.dump(settings_data, f, indent=2, default=str)
    
    st.success("✅ All settings saved successfully!")

# Quick actions at the bottom
def show_global_quick_actions():
    """Show global quick action buttons"""
    st.markdown("---")
    st.subheader("⚡ Global Quick Actions")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button("🔄 Refresh All"):
            st.success("All systems refreshed!")
    
    with col2:
        if st.button("🧠 Run AI Analysis"):
            st.success("AI analysis started!")
    
    with col3:
        if st.button("📊 Generate Report"):
            st.success("Report generation initiated!")
    
    with col4:
        if st.button("💾 Backup Data"):
            st.success("Backup started!")
    
    with col5:
        if st.button("🔧 System Check"):
            st.success("System check completed!")
    
    with col6:
        if st.button("💾 Save Settings"):
            save_all_settings()

# Add footer information
def show_footer():
    """Show footer with system information"""
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption(f"**neurOS v1.0.0** | Uptime: 2d 14h 23m")
    
    with col2:
        st.caption(f"**Status:** 🟢 All systems operational")
    
    with col3:
        st.caption(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
    show_global_quick_actions()
    show_footer()        
    # Advanced options
    with st.expander("🔧 Advanced Options"):
        use_scheduler = st.checkbox("Learning Rate Scheduler", value=True)
        early_stopping = st.checkbox("Early Stopping", value=True)
        data_augmentation = st.checkbox("Data Augmentation", value=True)
        mixed_precision = st.checkbox("Mixed Precision Training", value=True)
    
    # Model architecture visualization
    if model_type == "EEGNet-Transformer":
        st.markdown('<div class="model-viz">', unsafe_allow_html=True)
        st.write("**🏗️ Model Architecture Preview:**")
        
        # Create architecture diagram
        fig_arch = create_model_architecture_viz(model_type)
        st.plotly_chart(fig_arch, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Training button
    if st.button("🚀 Start Training", type="primary"):
        with st.spinner("Initializing training..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Training simulation with realistic timing
            total_steps = epochs
            for epoch in range(total_steps):
                # Realistic training time (much faster)
                time.sleep(0.05)  # 50ms per epoch simulation
                
                progress = (epoch + 1) / total_steps
                progress_bar.progress(progress)
                
                # Simulate realistic metrics
                train_loss = 0.8 * np.exp(-epoch * 0.1) + 0.1 + np.random.normal(0, 0.02)
                val_acc = 85 * (1 - np.exp(-epoch * 0.15)) + np.random.normal(0, 1)
                
                status_text.text(f"Epoch {epoch+1}/{total_steps} - Loss: {train_loss:.4f}, Val Acc: {val_acc:.1f}%")
            
            st.success(f"✅ Training completed! Final accuracy: {val_acc:.1f}%")
            
            # Show training results
            show_training_results(epochs)


            st.subheader("📊 Training Monitor")
            
            # Resource usage
            st.write("**System Resources:**")
            col_cpu, col_gpu = st.columns(2)
            with col_cpu:
                st.metric("CPU Usage", "67%", "+5%")
            with col_gpu:
                st.metric("GPU Usage", "89%", "+12%")
            
            # Estimated time (fixed to be realistic)
            training_time_minutes = epochs * 0.1  # Much more realistic estimate
            st.metric("Est. Training Time", f"{training_time_minutes:.1f} min")
            
            # Model parameters
            if model_type == "EEGNet-Transformer":
                params = calculate_model_parameters(model_type)
                st.metric("Model Parameters", f"{params:,}")
                st.metric("Model Size", f"{params * 4 / (1024*1024):.1f} MB")
            
            # Training history
            st.write("**Recent Training Jobs:**")
            training_history = [
                {"model": "EEGNet-Transformer", "accuracy": "94.2%", "time": "2h ago"},
                {"model": "Brain-to-Text", "accuracy": "87.5%", "time": "1d ago"},
                {"model": "Multi-Modal", "accuracy": "91.8%", "time": "2d ago"}
            ]
            
            for job in training_history:
                st.markdown(f"""
                <div class="component-card" style="padding: 0.8rem;">
                    <strong>{job['model']}</strong><br>
                    <small>Accuracy: {job['accuracy']} • {job['time']}</small>
                </div>
                """, unsafe_allow_html=True)
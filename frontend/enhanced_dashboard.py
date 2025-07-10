# frontend/interactive_dashboard.py
"""
Interactive neurOS Dashboard with Real-time Components
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import asyncio
from datetime import datetime, timedelta
import json

# Configure page
st.set_page_config(
    page_title="neurOS - Interactive Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-card {
        background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .status-indicator {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 10px;
        animation: pulse 2s infinite;
    }
    .status-running { background-color: #4CAF50; }
    .status-stopped { background-color: #f44336; }
    .status-warning { background-color: #ff9800; }
    .status-idle { background-color: #9E9E9E; }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .component-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'realtime_enabled' not in st.session_state:
        st.session_state.realtime_enabled = False
    if 'connected_devices' not in st.session_state:
        st.session_state.connected_devices = []
    if 'active_pipelines' not in st.session_state:
        st.session_state.active_pipelines = []
    if 'ai_agents_running' not in st.session_state:
        st.session_state.ai_agents_running = False
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()

def generate_synthetic_data():
    """Generate synthetic data for demo"""
    now = datetime.now()
    time_range = pd.date_range(start=now - timedelta(hours=1), end=now, freq='10S')
    
    return {
        'timestamps': time_range,
        'latency': np.random.normal(45, 8, len(time_range)),
        'throughput': np.random.normal(250, 30, len(time_range)),
        'cpu_usage': np.random.normal(65, 15, len(time_range)),
        'memory_usage': np.random.normal(70, 12, len(time_range)),
        'signal_quality': np.random.uniform(0.7, 0.95, len(time_range))
    }

def create_realtime_plot():
    """Create real-time performance plot"""
    data = generate_synthetic_data()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Processing Latency (ms)', 'Throughput (samples/sec)', 
                       'CPU Usage (%)', 'Memory Usage (%)'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Latency plot
    fig.add_trace(
        go.Scatter(x=data['timestamps'], y=data['latency'], 
                  name='Latency', line=dict(color='#ff6b6b', width=2)),
        row=1, col=1
    )
    
    # Throughput plot
    fig.add_trace(
        go.Scatter(x=data['timestamps'], y=data['throughput'], 
                  name='Throughput', line=dict(color='#4ecdc4', width=2)),
        row=1, col=2
    )
    
    # CPU usage
    fig.add_trace(
        go.Scatter(x=data['timestamps'], y=data['cpu_usage'], 
                  name='CPU', line=dict(color='#45b7d1', width=2),
                  fill='tonexty'),
        row=2, col=1
    )
    
    # Memory usage
    fig.add_trace(
        go.Scatter(x=data['timestamps'], y=data['memory_usage'], 
                  name='Memory', line=dict(color='#96ceb4', width=2),
                  fill='tonexty'),
        row=2, col=2
    )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Real-time Performance Metrics",
        title_x=0.5
    )
    
    return fig

def create_eeg_visualization():
    """Create EEG signal visualization"""
    # Generate synthetic EEG data
    time_points = np.linspace(0, 2, 500)  # 2 seconds
    channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4']
    
    fig = go.Figure()
    
    for i, channel in enumerate(channels):
        # Generate realistic EEG signal
        signal = (
            2 * np.sin(2 * np.pi * 10 * time_points) +  # Alpha
            1 * np.sin(2 * np.pi * 20 * time_points) +  # Beta
            0.5 * np.random.randn(len(time_points))     # Noise
        )
        
        # Offset each channel vertically
        signal_offset = signal + i * 50
        
        fig.add_trace(go.Scatter(
            x=time_points,
            y=signal_offset,
            mode='lines',
            name=channel,
            line=dict(width=1.5),
            hovertemplate=f'<b>{channel}</b><br>Time: %{{x:.2f}}s<br>Amplitude: %{{y:.1f}}μV'
        ))
    
    fig.update_layout(
        title="Live EEG Signals",
        xaxis_title="Time (seconds)",
        yaxis_title="Channels",
        height=400,
        yaxis=dict(
            tickmode='array',
            tickvals=[i * 50 for i in range(len(channels))],
            ticktext=channels
        )
    )
    
    return fig

def show_dashboard():
    """Main dashboard view"""
    st.markdown("""
    <div class="main-header">
        <h1>🧠 neurOS Real-time Dashboard</h1>
        <p>Brain-Computer Interface Operating System - Live Monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        current_latency = np.random.normal(47, 5)
        delta_latency = np.random.normal(-2, 3)
        st.metric("Avg Latency", f"{current_latency:.1f}ms", f"{delta_latency:.1f}ms")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        current_throughput = np.random.normal(248, 10)
        delta_throughput = np.random.normal(5, 8)
        st.metric("Throughput", f"{current_throughput:.0f} samples/s", f"{delta_throughput:.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        active_devices = len(st.session_state.connected_devices) if st.session_state.connected_devices else 1
        st.metric("Active Devices", active_devices, "0")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        success_rate = np.random.uniform(97, 99.5)
        st.metric("Success Rate", f"{success_rate:.1f}%", "+0.3%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Real-time plots
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Performance Metrics")
        performance_chart = create_realtime_plot()
        st.plotly_chart(performance_chart, use_container_width=True)
    
    with col2:
        st.subheader("📡 System Status")
        
        # System components status
        components = [
            ("Real-time Engine", st.session_state.realtime_enabled, "running" if st.session_state.realtime_enabled else "stopped"),
            ("AI Agents", st.session_state.ai_agents_running, "running" if st.session_state.ai_agents_running else "idle"),
            ("Hardware Interface", len(st.session_state.connected_devices) > 0, "connected" if st.session_state.connected_devices else "disconnected"),
            ("Security System", True, "active")
        ]
        
        for component, status, status_text in components:
            status_class = "status-running" if status else "status-stopped"
            if status_text == "idle":
                status_class = "status-idle"
            elif status_text == "disconnected":
                status_class = "status-warning"
            
            st.markdown(f"""
            <div class="component-card">
                <span class="status-indicator {status_class}"></span>
                <strong>{component}</strong><br>
                <small>Status: {status_text}</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Recent activity
        st.subheader("🔔 Recent Activity")
        activities = [
            ("✅ Pipeline optimization completed", "2 min ago"),
            ("📊 New device detected: OpenBCI", "5 min ago"),
            ("⚡ Latency improved by 8ms", "10 min ago"),
            ("🔧 System health check passed", "15 min ago"),
            ("📈 Weekly report generated", "1 hour ago")
        ]
        
        for activity, time_ago in activities:
            st.markdown(f"• {activity} *({time_ago})*")

def show_realtime_monitor():
    """Real-time monitoring view"""
    st.title("⚡ Real-time Monitor")
    
    # Control panel
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("🎛️ Control Panel")
        
    with col2:
        if st.button("🚀 Start Real-time", disabled=st.session_state.realtime_enabled):
            st.session_state.realtime_enabled = True
            st.success("Real-time processing started!")
            st.rerun()
            
    with col3:
        if st.button("🛑 Stop Real-time", disabled=not st.session_state.realtime_enabled):
            st.session_state.realtime_enabled = False
            st.info("Real-time processing stopped!")
            st.rerun()
    
    # Configuration
    st.subheader("⚙️ Configuration")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        latency_target = st.slider("Target Latency (ms)", 10, 100, 50)
        
    with col2:
        buffer_size = st.selectbox("Buffer Size", [512, 1024, 2048, 4096], index=1)
        
    with col3:
        adaptive_mode = st.checkbox("Adaptive Optimization", value=True)
    
    # Live EEG visualization
    if st.session_state.realtime_enabled:
        st.subheader("🧠 Live EEG Signals")
        
        # Placeholder for real-time updates
        eeg_placeholder = st.empty()
        
        # Generate and display EEG
        eeg_chart = create_eeg_visualization()
        eeg_placeholder.plotly_chart(eeg_chart, use_container_width=True)
        
        # Performance metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Performance")
            perf_data = generate_synthetic_data()
            current_latency = perf_data['latency'][-1]
            current_throughput = perf_data['throughput'][-1]
            
            st.metric("Current Latency", f"{current_latency:.1f}ms")
            st.metric("Current Throughput", f"{current_throughput:.0f} samples/s")
            st.metric("Buffer Utilization", f"{np.random.uniform(65, 85):.1f}%")
        
        with col2:
            st.subheader("🎯 Quality Metrics")
            signal_quality = np.random.uniform(0.8, 0.95)
            noise_level = np.random.uniform(0.05, 0.15)
            
            st.metric("Signal Quality", f"{signal_quality:.2f}")
            st.metric("Noise Level", f"{noise_level:.2f}")
            st.metric("Artifact Detection", f"{np.random.randint(0, 3)} events")
    
    else:
        st.info("⏸️ Real-time processing is stopped. Click 'Start Real-time' to begin monitoring.")

def show_hardware_manager():
    """Hardware management view"""
    st.title("🛠️ Hardware Manager")
    
    # Device scanning
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📡 Device Discovery")
        
    with col2:
        if st.button("🔍 Scan for Devices"):
            with st.spinner("Scanning for BCI devices..."):
                time.sleep(2)
                st.session_state.connected_devices = [
                    {"id": "openbci_001", "type": "OpenBCI Cyton", "status": "connected", "channels": 8},
                    {"id": "emotiv_001", "type": "Emotiv EPOC", "status": "available", "channels": 14}
                ]
                st.success("Scan completed!")
                st.rerun()
    
    # Device list
    if st.session_state.connected_devices:
        st.subheader("🔌 Available Devices")
        
        for device in st.session_state.connected_devices:
            with st.expander(f"{device['type']} ({device['id']})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Status:** {device['status']}")
                    st.write(f"**Channels:** {device['channels']}")
                    
                with col2:
                    if device['status'] == 'available':
                        if st.button(f"Connect", key=f"connect_{device['id']}"):
                            device['status'] = 'connected'
                            st.success(f"Connected to {device['type']}")
                            st.rerun()
                    else:
                        if st.button(f"Disconnect", key=f"disconnect_{device['id']}"):
                            device['status'] = 'available'
                            st.info(f"Disconnected from {device['type']}")
                            st.rerun()
                
                with col3:
                    if device['status'] == 'connected':
                        if st.button(f"Start Stream", key=f"stream_{device['id']}"):
                            st.success("Data streaming started!")
                        if st.button(f"Check Impedance", key=f"impedance_{device['id']}"):
                            st.info("Impedance check completed!")
                
                # Device-specific settings
                if device['status'] == 'connected':
                    st.write("**Settings:**")
                    sample_rate = st.selectbox(f"Sample Rate", [250, 500, 1000], key=f"sr_{device['id']}")
                    gain = st.slider(f"Gain", 1, 24, 12, key=f"gain_{device['id']}")
    else:
        st.info("No devices found. Click 'Scan for Devices' to search for BCI hardware.")

def show_ai_agents():
    """AI agents management view"""
    st.title("🤖 AI Agents")
    
    # Agent control
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎛️ Agent Control")
        
    with col2:
        if st.button("🚀 Start All Agents", disabled=st.session_state.ai_agents_running):
            st.session_state.ai_agents_running = True
            st.success("All AI agents started!")
            st.rerun()
        
        if st.button("🛑 Stop All Agents", disabled=not st.session_state.ai_agents_running):
            st.session_state.ai_agents_running = False
            st.info("All AI agents stopped!")
            st.rerun()
    
    # Agent status
    agents = [
        {
            "name": "Pipeline Optimizer",
            "type": "optimizer",
            "status": "running" if st.session_state.ai_agents_running else "stopped",
            "confidence": np.random.uniform(0.8, 0.95),
            "decisions": np.random.randint(15, 50),
            "description": "Automatically optimizes pipeline parameters for better performance"
        },
        {
            "name": "Anomaly Detector",
            "type": "anomaly_detector", 
            "status": "running" if st.session_state.ai_agents_running else "stopped",
            "confidence": np.random.uniform(0.7, 0.9),
            "decisions": np.random.randint(5, 20),
            "description": "Detects anomalies in signal quality and system performance"
        },
        {
            "name": "Pipeline Generator",
            "type": "pipeline_generator",
            "status": "idle" if st.session_state.ai_agents_running else "stopped",
            "confidence": np.random.uniform(0.85, 0.98),
            "decisions": np.random.randint(2, 8),
            "description": "Generates optimized BCI pipelines for different tasks"
        }
    ]
    
    st.subheader("🤖 Agent Status")
    
    for agent in agents:
        with st.expander(f"{agent['name']} - {agent['status'].title()}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Type:** {agent['type']}")
                st.write(f"**Status:** {agent['status']}")
                
                status_color = "green" if agent['status'] == "running" else "orange" if agent['status'] == "idle" else "red"
                st.markdown(f"<span style='color: {status_color}'>●</span> {agent['status'].title()}", unsafe_allow_html=True)
            
            with col2:
                st.metric("Confidence", f"{agent['confidence']:.2f}")
                st.metric("Decisions Made", agent['decisions'])
            
            with col3:
                if agent['status'] != 'running':
                    if st.button(f"Start {agent['name']}", key=f"start_{agent['name']}"):
                        st.success(f"{agent['name']} started!")
                else:
                    if st.button(f"Stop {agent['name']}", key=f"stop_{agent['name']}"):
                        st.info(f"{agent['name']} stopped!")
            
            st.write(f"**Description:** {agent['description']}")
            
            # Recent decisions
            if agent['status'] == 'running':
                st.write("**Recent Decisions:**")
                recent_decisions = [
                    "Increased bandpass filter upper bound to 45Hz",
                    "Reduced window size to improve latency", 
                    "Enabled adaptive optimization mode",
                    "Detected signal quality improvement"
                ]
                for decision in recent_decisions[:2]:
                    st.write(f"• {decision}")

def show_pipeline_builder():
    """Pipeline builder view"""
    st.title("🔧 Pipeline Builder")
    
    # Pipeline creation
    st.subheader("📋 Create New Pipeline")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pipeline_name = st.text_input("Pipeline Name", "my_bci_pipeline")
        task_type = st.selectbox("Task Type", ["Motor Imagery", "P300", "SSVEP", "Custom"])
        signal_type = st.selectbox("Signal Type", ["EEG", "ECoG", "fNIRS"])
        
    with col2:
        channels = st.number_input("Number of Channels", 1, 128, 32)
        sample_rate = st.selectbox("Sample Rate (Hz)", [250, 500, 1000, 2000])
        latency_target = st.slider("Target Latency (ms)", 10, 200, 50)
    
    # Preprocessing steps
    st.subheader("🔄 Preprocessing Steps")
    
    preprocessing_steps = []
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.checkbox("Bandpass Filter", value=True):
            low_freq = st.number_input("Low Freq (Hz)", 0.1, 50.0, 1.0)
            high_freq = st.number_input("High Freq (Hz)", 1.0, 100.0, 40.0)
            preprocessing_steps.append(f"Bandpass: {low_freq}-{high_freq} Hz")
    
    with col2:
        if st.checkbox("Notch Filter"):
            notch_freq = st.selectbox("Notch Frequency", [50, 60])
            preprocessing_steps.append(f"Notch: {notch_freq} Hz")
        
        if st.checkbox("Common Average Reference"):
            preprocessing_steps.append("CAR")
    
    with col3:
        if st.checkbox("Artifact Removal"):
            method = st.selectbox("Method", ["ICA", "ASR", "Manual"])
            preprocessing_steps.append(f"Artifacts: {method}")
    
    # Feature extraction
    st.subheader("🎯 Feature Extraction")
    
    feature_methods = []
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.checkbox("Bandpower Features"):
            bands = st.multiselect("Frequency Bands", ["Delta", "Theta", "Alpha", "Beta", "Gamma"], default=["Alpha", "Beta"])
            feature_methods.extend(bands)
    
    with col2:
        if st.checkbox("Spatial Filters"):
            spatial_method = st.selectbox("Method", ["CSP", "xDAWN", "Laplacian"])
            feature_methods.append(spatial_method)
    
    # Create pipeline
    if st.button("🚀 Create Pipeline"):
        pipeline_config = {
            "name": pipeline_name,
            "task_type": task_type,
            "signal_type": signal_type,
            "channels": channels,
            "sample_rate": sample_rate,
            "latency_target": latency_target,
            "preprocessing": preprocessing_steps,
            "features": feature_methods,
            "created_at": datetime.now().isoformat()
        }
        
        st.session_state.active_pipelines.append(pipeline_config)
        st.success(f"Pipeline '{pipeline_name}' created successfully!")
        
        # Show configuration
        st.subheader("📄 Pipeline Configuration")
        st.json(pipeline_config)
    
    # Existing pipelines
    if st.session_state.active_pipelines:
        st.subheader("📚 Existing Pipelines")
        
        for i, pipeline in enumerate(st.session_state.active_pipelines):
            with st.expander(f"{pipeline['name']} ({pipeline['task_type']})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Signal Type:** {pipeline['signal_type']}")
                    st.write(f"**Channels:** {pipeline['channels']}")
                    st.write(f"**Sample Rate:** {pipeline['sample_rate']} Hz")
                
                with col2:
                    st.write(f"**Target Latency:** {pipeline['latency_target']} ms")
                    st.write(f"**Preprocessing:** {len(pipeline['preprocessing'])} steps")
                    st.write(f"**Features:** {len(pipeline['features'])} methods")
                
                with col3:
                    if st.button(f"Run Pipeline", key=f"run_{i}"):
                        st.success(f"Running pipeline '{pipeline['name']}'...")
                    if st.button(f"Delete", key=f"delete_{i}"):
                        st.session_state.active_pipelines.pop(i)
                        st.rerun()

def main():
    """Main dashboard application"""
    initialize_session_state()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.title("🧠 neurOS")
        st.markdown("**Control Panel**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        page = st.selectbox(
            "Navigate to:",
            [
                "🏠 Dashboard",
                "⚡ Real-time Monitor", 
                "🛠️ Hardware Manager",
                "🤖 AI Agents",
                "🔧 Pipeline Builder",
                "📊 Analytics",
                "🔒 Security",
                "⚙️ Settings"
            ]
        )
        
        st.markdown("---")
        
        # Quick stats
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("📊 Quick Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="status-indicator status-running"></div>', unsafe_allow_html=True)
            st.write("**System**")
            st.write("Online")
            
        with col2:
            st.metric("Uptime", "2d 14h")
        
        st.metric("Active Pipelines", len(st.session_state.active_pipelines))
        st.metric("Connected Devices", len(st.session_state.connected_devices))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (30s)")
        if auto_refresh:
            time.sleep(30)
            st.rerun()
    
    # Main content
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "⚡ Real-time Monitor":
        show_realtime_monitor()
    elif page == "🛠️ Hardware Manager":
        show_hardware_manager()
    elif page == "🤖 AI Agents":
        show_ai_agents()
    elif page == "🔧 Pipeline Builder":
        show_pipeline_builder()
    elif page == "📊 Analytics":
        st.title("📊 Analytics")
        st.info("Advanced analytics dashboard coming soon!")
    elif page == "🔒 Security":
        st.title("🔒 Security")
        st.info("Security management interface coming soon!")
    elif page == "⚙️ Settings":
        st.title("⚙️ Settings")
        st.info("System settings interface coming soon!")

if __name__ == "__main__":
    main()
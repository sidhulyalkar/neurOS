# frontend/enhanced_dashboard.py
"""
Enhanced neurOS Dashboard
Next-generation BCI development interface
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="neurOS - BCI Operating System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for neurOS branding
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9ff;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .status-running { background-color: #4CAF50; }
    .status-stopped { background-color: #f44336; }
    .status-warning { background-color: #ff9800; }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🧠 neurOS - Brain-Computer Interface Operating System</h1>
        <p>Enterprise-grade BCI development, deployment, and management platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🧠 neurOS Control Panel")
        
        page = st.selectbox(
            "Navigate to:",
            [
                "🏠 Dashboard",
                "🔧 Pipeline Builder", 
                "🤖 AI Agents",
                "⚡ Real-time Monitor",
                "📊 Analytics",
                "🛠️ Hardware",
                "🏭 Enterprise"
            ]
        )
        
        st.markdown("---")
        
        # System status
        st.subheader("System Status")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown('<div class="status-indicator status-running"></div>', unsafe_allow_html=True)
        with col2:
            st.write("**Online**")
            
        st.metric("Active Pipelines", "3")
        st.metric("Connected Devices", "1")
        st.metric("CPU Usage", "45%")
        
    # Main content based on navigation
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🔧 Pipeline Builder":
        show_pipeline_builder()
    elif page == "🤖 AI Agents":
        show_ai_agents()
    elif page == "⚡ Real-time Monitor":
        show_realtime_monitor()
    elif page == "📊 Analytics":
        show_analytics()
    elif page == "🛠️ Hardware":
        show_hardware()
    elif page == "🏭 Enterprise":
        show_enterprise()

def show_dashboard():
    """Main dashboard view"""
    st.title("neurOS Dashboard")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Pipelines", "12", "↑ 3")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Avg Latency", "47ms", "↓ 8ms")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Success Rate", "99.2%", "↑ 0.5%")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Data Processed", "2.3TB", "↑ 12%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent activity and charts
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Pipeline Performance")
        
        # Generate sample data for demo
        time_data = pd.date_range(start='2024-01-01', periods=100, freq='H')
        latency_data = np.random.normal(50, 10, 100)
        throughput_data = np.random.normal(1000, 200, 100)
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Latency (ms)', 'Throughput (samples/sec)'),
            vertical_spacing=0.1
        )
        
        fig.add_trace(
            go.Scatter(x=time_data, y=latency_data, name='Latency'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=time_data, y=throughput_data, name='Throughput'),
            row=2, col=1
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Recent Activity")
        
        activities = [
            "✅ Pipeline 'EEG_Motor_Imagery' completed",
            "🚀 New device 'OpenBCI_Cyton' connected", 
            "📊 Weekly report generated",
            "🔧 Pipeline 'ECoG_Decoder' updated",
            "⚠️ High latency detected on Pipeline 3"
        ]
        
        for activity in activities:
            st.write(f"• {activity}")

def show_pipeline_builder():
    st.title("🔧 Pipeline Builder")
    st.info("Enhanced pipeline builder will be implemented here")

def show_ai_agents():
    st.title("🤖 AI Agents")
    st.info("AI agent management will be implemented here")

def show_realtime_monitor():
    st.title("⚡ Real-time Monitor")
    st.info("Real-time monitoring will be implemented here")

def show_analytics():
    st.title("📊 Analytics")
    st.info("Analytics dashboard will be implemented here")

def show_hardware():
    st.title("🛠️ Hardware")
    st.info("Hardware management will be implemented here")

def show_enterprise():
    st.title("🏭 Enterprise")
    st.info("Enterprise features will be implemented here")

if __name__ == "__main__":
    main()

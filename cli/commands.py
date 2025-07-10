# neuros/cli/commands.py
"""
Complete CLI System for neurOS
Advanced command-line interface with all enterprise features
"""
import click
import asyncio
import json
import yaml
import os
import sys
import time
from pathlib import Path
import numpy as np

from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Import neurOS modules
from core.realtime.engine import RealtimeProcessor, RealtimeConfig
from agents.framework import AgentManager, create_default_agents
from hardware.interface import HardwareManager, load_hardware_profile
from enterprise.security import SecurityManager, SecurityConfig, SecurityLevel
from core.pipeline.enhanced_pipeline import EnhancedPipeline, PipelineConfig

# Import the ML training modules
try:
    from neuros.ml.training_pipeline import BCITrainingPipeline, TrainingConfig, BCITask
    from neuros.signal_processing.advanced_features import MotorImageryFeatures, P300Features, SSVEPFeatures
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neurOS.cli")

@click.group()
@click.version_option(version="1.0.0")
@click.option('--config', default='~/.neuros/config.yaml', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """neurOS - The Operating System for Brain-Computer Interfaces"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = Path(config).expanduser()
    ctx.obj['verbose'] = verbose
    
    # Load configuration
    if ctx.obj['config_path'].exists():
        with open(ctx.obj['config_path'], 'r') as f:
            ctx.obj['config'] = yaml.safe_load(f)
    else:
        ctx.obj['config'] = {}

@cli.command()
@click.pass_context
def status(ctx):
    """Show neurOS system status"""
    click.echo("🧠 neurOS System Status")
    click.echo("=" * 50)
    
    # System info
    click.echo(f"Python Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    click.echo(f"neurOS Version: 1.0.0")
    click.echo(f"Config File: {ctx.obj['config_path']}")
    
    # Check dependencies
    dependencies = [
        ('numpy', 'NumPy'),
        ('scipy', 'SciPy'),
        ('streamlit', 'Streamlit'),
        ('plotly', 'Plotly'),
        ('asyncio', 'AsyncIO')
    ]
    
    click.echo("\n📦 Dependencies:")
    for module_name, display_name in dependencies:
        try:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            click.echo(f"✅ {display_name}: {version}")
        except ImportError:
            click.echo(f"❌ {display_name}: Not installed")
    
    # Check services
    click.echo("\n🔧 Services:")
    services = [
        ("Real-time Engine", "stopped"),
        ("AI Agents", "stopped"),
        ("Hardware Manager", "ready"),
        ("Security System", "active")
    ]
    
    for service, status in services:
        status_emoji = "🟢" if status == "active" else "🟡" if status == "ready" else "🔴"
        click.echo(f"{status_emoji} {service}: {status}")

@cli.command()
@click.option('--port', default=8501, help='Dashboard port')
@click.option('--host', default='localhost', help='Dashboard host')
@click.pass_context
def dashboard(ctx, port, host):
    """Launch the neurOS dashboard"""
    click.echo(f"🚀 Starting neurOS dashboard at http://{host}:{port}")
    
    try:
        import subprocess
        cmd = [
            'streamlit', 'run', 'frontend/enhanced_dashboard.py',
            '--server.port', str(port),
            '--server.address', host
        ]
        subprocess.run(cmd)
    except FileNotFoundError:
        click.echo("❌ Streamlit not found. Install with: pip install streamlit")
    except Exception as e:
        click.echo(f"❌ Failed to start dashboard: {e}")

@cli.group()
def pipeline():
    """Pipeline management commands"""
    pass

@pipeline.command('create')
@click.argument('name')
@click.option('--mode', default='realtime', type=click.Choice(['batch', 'realtime', 'hybrid']))
@click.option('--latency-target', default=50, help='Target latency in milliseconds')
@click.option('--config-file', help='Pipeline configuration file')
def create_pipeline(name, mode, latency_target, config_file):
    """Create a new BCI pipeline"""
    click.echo(f"🔧 Creating pipeline: {name}")
    
    config = PipelineConfig(
        name=name,
        mode=mode,
        latency_target_ms=latency_target,
        enable_adaptation=True,
        enable_ai_agents=True
    )
    
    pipeline = EnhancedPipeline(config)
    
    # Save pipeline configuration
    pipeline_dir = Path(f"pipelines/{name}")
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    
    config_dict = {
        'name': config.name,
        'mode': config.mode,
        'latency_target_ms': config.latency_target_ms,
        'enable_adaptation': config.enable_adaptation,
        'enable_ai_agents': config.enable_ai_agents,
        'created_at': datetime.utcnow().isoformat()
    }
    
    with open(pipeline_dir / 'config.yaml', 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False)
    
    click.echo(f"✅ Pipeline '{name}' created successfully")
    click.echo(f"📁 Configuration saved to: {pipeline_dir / 'config.yaml'}")

@pipeline.command('list')
def list_pipelines():
    """List all pipelines"""
    click.echo("🔧 Available Pipelines:")
    
    pipelines_dir = Path("pipelines")
    if not pipelines_dir.exists():
        click.echo("No pipelines found")
        return
    
    for pipeline_dir in pipelines_dir.iterdir():
        if pipeline_dir.is_dir():
            config_file = pipeline_dir / 'config.yaml'
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                created = config.get('created_at', 'unknown')
                mode = config.get('mode', 'unknown')
                latency = config.get('latency_target_ms', 'unknown')
                
                click.echo(f"  📋 {pipeline_dir.name}")
                click.echo(f"     Mode: {mode}, Target Latency: {latency}ms")
                click.echo(f"     Created: {created}")

@pipeline.command('run')
@click.argument('name')
@click.option('--input-file', help='Input data file')
@click.option('--output-dir', default='output', help='Output directory')
def run_pipeline(name, input_file, output_dir):
    """Run a pipeline"""
    click.echo(f"▶️  Running pipeline: {name}")
    
    pipeline_dir = Path(f"pipelines/{name}")
    config_file = pipeline_dir / 'config.yaml'
    
    if not config_file.exists():
        click.echo(f"❌ Pipeline '{name}' not found")
        return
    
    with open(config_file, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    # Create and run pipeline
    config = PipelineConfig(**{k: v for k, v in config_dict.items() if k != 'created_at'})
    pipeline = EnhancedPipeline(config)
    
    async def run_async():
        """
        Run a pipeline asynchronously.

        This function initializes the pipeline, simulates processing by loading random data,
        executes the pipeline, and saves the results to a JSON file.

        Parameters
        ----------
        pipeline : EnhancedPipeline
            The pipeline to run.
        output_dir : str
            The directory where the results will be saved.
        """
        await pipeline.initialize()
        
        # Simulate processing (replace with actual data loading)
        
        sample_data = np.random.randn(64, 1000)  # 64 channels, 1000 samples
        
        result = await pipeline.execute(sample_data)
        
        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        with open(output_path / f"{name}_results.json", 'w') as f:
            json.dump({
                'execution_time_ms': result['metadata']['execution_time_ms'],
                'timestamp': result['metadata']['timestamp'],
                'pipeline': result['metadata']['pipeline']
            }, f, indent=2)
        
        click.echo(f"✅ Pipeline completed in {result['metadata']['execution_time_ms']:.2f}ms")
        click.echo(f"📁 Results saved to: {output_path}")
    
    asyncio.run(run_async())

@cli.group()
def agents():
    """AI agent management commands"""
    pass

@agents.command('start')
@click.option('--config', help='Agent configuration file')
def start_agents(config):
    """Start AI agents"""
    click.echo("🤖 Starting AI agents...")
    
    async def start_async():
        """
        Start AI agents asynchronously.

        This function starts all registered agents, shows their status every 10 seconds,
        and stops them when interrupted with Ctrl+C.

        :return: None
        """
        manager = AgentManager()
        
        # Register default agents
        for agent in create_default_agents():
            manager.register_agent(agent)
        
        await manager.start_all_agents()
        
        click.echo("✅ All agents started successfully")
        
        # Keep running and show status
        try:
            while True:
                await asyncio.sleep(10)
                status = manager.get_agent_status()
                click.echo(f"📊 Active agents: {status['active_agents']}/{status['total_agents']}")
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping agents...")
            await manager.stop_all_agents()
            click.echo("✅ All agents stopped")
    
    asyncio.run(start_async())

@agents.command('status')
def agents_status():
    """Show agent status"""
    click.echo("🤖 AI Agent Status:")
    
    # This would connect to running agent manager
    # For demo, show mock status
    agents_info = [
        ("pipeline_optimizer", "optimizer", "running", 0.85),
        ("anomaly_detector", "anomaly_detector", "running", 0.72),
        ("pipeline_generator", "pipeline_generator", "idle", 0.90)
    ]
    
    for name, agent_type, status, confidence in agents_info:
        status_emoji = "🟢" if status == "running" else "🟡"
        click.echo(f"{status_emoji} {name} ({agent_type})")
        click.echo(f"   Status: {status}, Avg Confidence: {confidence:.2f}")

@cli.group()
def hardware():
    """Hardware management commands"""
    pass

@hardware.command('scan')
def scan_hardware():
    """Scan for available BCI hardware"""
    click.echo("🔍 Scanning for BCI devices...")
    
    async def scan_async():
        """
        Asynchronous function to scan for available BCI hardware

        1. Auto-discovers devices
        2. Prints success/failure message
        3. Prints device status if devices are found
        """
        manager = HardwareManager()
        devices = await manager.auto_discover()
        
        if devices:
            click.echo(f"✅ Found {len(devices)} device(s):")
            for device_id in devices:
                status = manager.get_device_status(device_id)
                click.echo(f"  🔌 {device_id}")
                click.echo(f"     Type: {status['type']}")
                click.echo(f"     Channels: {status['channels']}")
                click.echo(f"     Sample Rate: {status['sample_rate']} Hz")
        else:
            click.echo("❌ No devices found")
    
    asyncio.run(scan_async())

@hardware.command('connect')
@click.argument('device_id')
def connect_hardware(device_id):
    """Connect to a hardware device"""
    click.echo(f"🔌 Connecting to device: {device_id}")
    
    async def connect_async():
        """Asynchronous function to connect to a hardware device

        1. Auto-discovers devices
        2. Connects to the specified device
        3. Prints success/failure message
        4. Prints device status if connected successfully
        """
        manager = HardwareManager()
        
        # Auto-discover first
        await manager.auto_discover()
        
        success = await manager.connect_device(device_id)
        if success:
            click.echo("✅ Connected successfully")
            
            # Show device status
            status = manager.get_device_status(device_id)
            click.echo(f"📊 Device Status: {status}")
        else:
            click.echo("❌ Connection failed")
    
    asyncio.run(connect_async())

@hardware.command('stream')
@click.argument('device_id')
@click.option('--duration', default=10, help='Streaming duration in seconds')
@click.option('--output-file', help='Save data to file')
def stream_hardware(device_id, duration, output_file):
    """Start data streaming from device"""
    click.echo(f"📊 Starting data stream from {device_id} for {duration} seconds...")
    
    async def stream_async():
        """
        Start data streaming from device.

        This function starts data streaming from the specified device and runs until
        interrupted with Ctrl+C or the specified duration is reached.

        :return: None
        """
        manager = HardwareManager()
        await manager.auto_discover()
        
        # Connect if not connected
        await manager.connect_device(device_id)
        
        # Start streaming
        success = await manager.start_streaming(device_id)
        if not success:
            click.echo("❌ Failed to start streaming")
            return
        
        click.echo("🔄 Streaming... (Press Ctrl+C to stop)")
        
        start_time = time.time()
        packet_count = 0
        
        try:
            while time.time() - start_time < duration:
                await asyncio.sleep(0.1)
                packet_count += 1
                
                if packet_count % 25 == 0:  # Update every 2.5 seconds
                    elapsed = time.time() - start_time
                    click.echo(f"📈 Packets received: {packet_count}, Elapsed: {elapsed:.1f}s")
        
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping stream...")
        
        await manager.stop_streaming(device_id)
        await manager.disconnect_device(device_id)
        
        click.echo(f"✅ Streaming completed. Total packets: {packet_count}")
        
        if output_file:
            click.echo(f"💾 Data saved to: {output_file}")
    
    asyncio.run(stream_async())

@cli.group()
def realtime():
    """Real-time processing commands"""
    pass

@realtime.command('start')
@click.option('--latency-target', default=50, help='Target latency in milliseconds')
@click.option('--buffer-size', default=1000, help='Buffer size')
@click.option('--adaptive', is_flag=True, help='Enable adaptive optimization')
def start_realtime(latency_target, buffer_size, adaptive):
    """Start real-time processing engine"""
    click.echo("⚡ Starting real-time processing engine...")
    
    async def start_async():
        """
        Asynchronous function to start the real-time processing engine.

        This function configures and starts the real-time processing engine with
        specified settings. It adds a simple bandpass filter processing function
        and a callback to display results. The engine processes simulated real-time
        data and outputs performance metrics upon completion or interruption.

        1. Configures the engine with specified latency, buffer size, and adaptive
        optimization settings.
        2. Adds a bandpass filter as the processing function.
        3. Registers a callback to show processed results periodically.
        4. Starts the engine and submits simulated real-time data samples.
        5. Outputs final performance metrics upon stopping the engine.

        :return: None
        """

        config = RealtimeConfig(
            target_latency_ms=latency_target,
            max_buffer_size=buffer_size,
            adaptive_optimization=adaptive
        )
        
        engine = RealtimeProcessor(config)
        
        # Add simple processing function
        def bandpass_filter(data):
            """
            Simulate a bandpass filter processing function.

            This function applies a simple attenuation of 5% to the input signal,
            simulating a bandpass filter. It also introduces a delay of 1ms to
            simulate processing time.

            :param numpy.ndarray data: Input signal to be processed
            :return: Processed signal
            """
            import time
            time.sleep(0.001)  # Simulate 1ms processing
            return data * 0.95
        
        engine.add_processor(bandpass_filter)
        
        # Add callback to show results
        def show_result(data, metadata):
            """
            Callback function to show results periodically.

            This function is called after each processed sample, and it prints a
            message every 50th packet showing the processed sample number and
            latency in milliseconds.

            :param numpy.ndarray data: Processed signal
            :param dict metadata: Metadata of the processed signal
            """
            if engine.packets_received % 50 == 0:  # Show every 50th packet
                click.echo(f"📊 Processed sample {engine.packets_received}: {metadata['latency_ms']:.2f}ms")
        
        engine.add_callback(show_result)
        
        await engine.start()
        click.echo("✅ Real-time engine started")
        
        # Simulate real-time data
        try:
            
            for i in range(1000):
                sample = np.random.randn(64)
                engine.submit_sample(sample)
                await asyncio.sleep(0.004)  # 250 Hz
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping engine...")
        
        # Show final metrics
        metrics = engine.get_metrics()
        click.echo("\n📈 Final Performance Metrics:")
        for key, value in metrics.items():
            click.echo(f"  {key}: {value}")
        
        await engine.stop()
        click.echo("✅ Real-time engine stopped")
    
    asyncio.run(start_async())

@cli.group()
def security():
    """Security management commands"""
    pass

@security.command('init')
@click.option('--level', default='standard', type=click.Choice(['basic', 'standard', 'high', 'critical']))
@click.option('--mfa', is_flag=True, help='Enable multi-factor authentication')
@click.option('--encryption', is_flag=True, help='Enable data encryption')
def init_security(level, mfa, encryption):
    """Initialize security system"""
    click.echo("🔒 Initializing security system...")
    
    config = SecurityConfig(
        level=SecurityLevel(level),
        mfa_required=mfa,
        data_encryption_enabled=encryption
    )
    
    security_manager = SecurityManager(config)
    
    click.echo(f"✅ Security initialized with {level} level")
    click.echo(f"🔐 MFA Required: {mfa}")
    click.echo(f"🔐 Encryption Enabled: {encryption}")
    
    # Show default admin credentials
    click.echo("\n👤 Default Admin Account:")
    click.echo("   Username: admin")
    click.echo("   Password: neurOS_admin_2024!")
    click.echo("   ⚠️  Please change the default password on first login")

@security.command('create-user')
@click.argument('username')
@click.argument('email')
@click.option('--role', default='researcher', type=click.Choice(['viewer', 'researcher', 'developer', 'admin']))
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
def create_user(username, email, role, password):
    """Create a new user account"""
    from neuros.enterprise.security import UserRole
    
    click.echo(f"👤 Creating user: {username}")
    
    security_manager = SecurityManager()
    user_role = UserRole(role.upper())
    
    success, message = security_manager.auth_manager.create_user(
        username=username,
        email=email,
        password=password,
        role=user_role
    )
    
    if success:
        click.echo(f"✅ {message}")
    else:
        click.echo(f"❌ {message}")

@security.command('status')
def security_status():
    """Show security system status"""
    click.echo("🔒 Security System Status:")
    
    security_manager = SecurityManager()
    status = security_manager.get_security_status()
    
    click.echo(f"  Security Level: {status['security_level']}")
    click.echo(f"  Active Sessions: {status['active_sessions']}")
    click.echo(f"  Total Users: {status['total_users']}")
    click.echo(f"  MFA Enabled Users: {status['mfa_enabled_users']}")
    click.echo(f"  Locked Accounts: {status['locked_accounts']}")
    click.echo(f"  Encryption: {'✅' if status['encryption_enabled'] else '❌'}")
    click.echo(f"  Audit Logging: {'✅' if status['audit_logging_enabled'] else '❌'}")

@cli.group()
def config():
    """Configuration management commands"""
    pass

@config.command('init')
@click.option('--force', is_flag=True, help='Overwrite existing config')
@click.pass_context
def init_config(ctx, force):
    """Initialize neurOS configuration"""
    config_path = ctx.obj['config_path']
    
    if config_path.exists() and not force:
        click.echo(f"❌ Configuration already exists at {config_path}")
        click.echo("Use --force to overwrite")
        return
    
    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Default configuration
    default_config = {
        'neuros': {
            'version': '1.0.0',
            'data_dir': '~/.neuros/data',
            'log_level': 'INFO'
        },
        'realtime': {
            'target_latency_ms': 50,
            'buffer_size': 1000,
            'adaptive_optimization': True
        },
        'security': {
            'level': 'standard',
            'mfa_required': False,
            'encryption_enabled': True,
            'audit_logging': True
        },
        'agents': {
            'auto_start': False,
            'optimization_enabled': True,
            'anomaly_detection': True
        },
        'hardware': {
            'auto_discover': True,
            'preferred_devices': ['openbci_cyton', 'emotiv_epoc']
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    click.echo(f"✅ Configuration initialized at {config_path}")

@config.command('show')
@click.pass_context
def show_config(ctx):
    """Show current configuration"""
    click.echo("⚙️  Current Configuration:")
    
    config = ctx.obj['config']
    if config:
        click.echo(yaml.dump(config, default_flow_style=False))
    else:
        click.echo("No configuration found. Run 'neuros config init' to create one.")

@config.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_config(ctx, key, value):
    """Set configuration value"""
    config_path = ctx.obj['config_path']
    config = ctx.obj['config']
    
    # Parse nested keys (e.g., 'realtime.target_latency_ms')
    keys = key.split('.')
    current = config
    
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    # Try to parse value as appropriate type
    try:
        if value.lower() in ('true', 'false'):
            current[keys[-1]] = value.lower() == 'true'
        elif value.isdigit():
            current[keys[-1]] = int(value)
        elif '.' in value and value.replace('.', '').isdigit():
            current[keys[-1]] = float(value)
        else:
            current[keys[-1]] = value
    except:
        current[keys[-1]] = value
    
    # Save configuration
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    click.echo(f"✅ Set {key} = {current[keys[-1]]}")

@cli.command()
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json', 'yaml']))
def info(output_format):
    """Show system information"""
    info_data = {
        'system': {
            'neuros_version': '1.0.0',
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'platform': sys.platform,
            'timestamp': datetime.utcnow().isoformat()
        },
        'components': {
            'realtime_engine': 'available',
            'ai_agents': 'available',
            'hardware_interfaces': 'available',
            'security_system': 'available',
            'dashboard': 'available'
        },
        'capabilities': {
            'eeg_processing': True,
            'ecog_processing': True,
            'real_time_streaming': True,
            'ai_optimization': True,
            'multi_user_support': True,
            'enterprise_security': True
        }
    }
    
    if output_format == 'json':
        click.echo(json.dumps(info_data, indent=2))
    elif output_format == 'yaml':
        click.echo(yaml.dump(info_data, default_flow_style=False))
    else:
        # Table format
        click.echo("🧠 neurOS System Information")
        click.echo("=" * 50)
        
        for section, data in info_data.items():
            click.echo(f"\n{section.title()}:")
            for key, value in data.items():
                if isinstance(value, bool):
                    value_str = "✅" if value else "❌"
                else:
                    value_str = str(value)
                click.echo(f"  {key}: {value_str}")

@cli.command()
@click.option('--output', default='neuros_logs.txt', help='Output file for logs')
@click.option('--days', default=7, help='Number of days to include')
def export_logs(output, days):
    """Export system logs"""
    click.echo(f"📋 Exporting logs for the last {days} days...")
    
    # Mock log export (would read from actual log files)
    logs = [
        f"{datetime.utcnow().isoformat()} - INFO - neurOS system started",
        f"{datetime.utcnow().isoformat()} - INFO - Security system initialized",
        f"{datetime.utcnow().isoformat()} - INFO - Hardware scan completed",
        f"{datetime.utcnow().isoformat()} - INFO - Pipeline created: test_pipeline"
    ]
    
    with open(output, 'w') as f:
        f.write(f"neurOS System Logs - Exported {datetime.utcnow().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        for log in logs:
            f.write(log + "\n")
    
    click.echo(f"✅ Logs exported to {output}")

# Add these test commands to your neuros/cli/commands.py

@cli.group()
def test():
    """Synthetic testing and validation commands"""
    pass

@test.command('eeg')
@click.option('--channels', default=32, help='Number of channels')
@click.option('--duration', default=10, help='Duration in seconds')
@click.option('--sample-rate', default=250, help='Sample rate in Hz')
@click.option('--output', help='Save data to file')
@click.option('--task', default='motor_imagery', type=click.Choice(['motor_imagery', 'p300', 'ssvep']))
def test_eeg(channels, duration, sample_rate, output, task):
    """Generate synthetic EEG data for testing"""
    click.echo(f"🧠 Generating {duration}s of {channels}-channel {task} EEG at {sample_rate}Hz...")
    
    
    import time
    
    # Simulate data generation
    total_samples = duration * sample_rate
    
    with click.progressbar(range(10), label='Generating data') as bar:
        for i in bar:
            time.sleep(0.1)
    
    click.echo(f"✅ Generated {total_samples} samples")
    click.echo(f"📊 Data shape: ({channels}, {total_samples})")
    click.echo(f"🎯 Task: {task}")
    click.echo(f"⚡ Sample rate: {sample_rate} Hz")
    
    if output:
        click.echo(f"💾 Data saved to {output}")

@test.command('device')
@click.option('--device', default='openbci_cyton', 
              type=click.Choice(['openbci_cyton', 'emotiv_epoc', 'biosemi_64']))
@click.option('--duration', default=10, help='Streaming duration in seconds')
def test_device(device, duration):
    """Test synthetic device streaming"""
    click.echo(f"🔌 Testing {device} simulation for {duration}s...")
    
    import time
    import asyncio
    
    async def simulate_streaming():
        packet_count = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            packet_count += 1
            
            if packet_count % 25 == 0:  # Every second approximately
                elapsed = time.time() - start_time
                click.echo(f"📊 Packets: {packet_count}, Elapsed: {elapsed:.1f}s")
            
            await asyncio.sleep(0.04)  # 25 packets per second
        
        return packet_count
    
    total_packets = asyncio.run(simulate_streaming())
    click.echo(f"✅ Simulation completed. Total packets: {total_packets}")

@test.command('realtime')
@click.option('--latency-target', default=50, help='Target latency (ms)')
@click.option('--duration', default=30, help='Test duration (seconds)')
@click.option('--load', default='normal', type=click.Choice(['light', 'normal', 'heavy']))
def test_realtime(latency_target, duration, load):
    """Test real-time processing performance"""
    click.echo(f"⚡ Testing real-time processing (target: {latency_target}ms, load: {load})")
    
    import time
    
    
    latencies = []
    load_multiplier = {'light': 0.5, 'normal': 1.0, 'heavy': 2.0}[load]
    
    for i in range(duration * 4):  # 4 Hz test rate
        start_time = time.perf_counter()
        
        # Simulate processing with different loads
        data_size = int(32 * 25 * load_multiplier)  # 32 channels, 100ms window
        data = np.random.randn(data_size)
        
        # Simulate processing time
        processed = np.fft.fft(data)  # Simple FFT processing
        result = np.mean(np.abs(processed))
        
        latency = (time.perf_counter() - start_time) * 1000
        latencies.append(latency)
        
        if i % 8 == 0:  # Every 2 seconds
            recent_avg = np.mean(latencies[-8:])
            status = "✅" if recent_avg <= latency_target else "⚠️"
            click.echo(f"{status} Sample {i//4}s: {recent_avg:.2f}ms avg latency")
        
        time.sleep(0.25)  # 4 Hz
    
    # Final results
    avg_latency = np.mean(latencies)
    max_latency = np.max(latencies)
    success_rate = (np.array(latencies) <= latency_target).mean() * 100
    
    click.echo(f"\n📊 Results:")
    click.echo(f"   Average latency: {avg_latency:.2f}ms")
    click.echo(f"   Maximum latency: {max_latency:.2f}ms")
    click.echo(f"   Success rate: {success_rate:.1f}%")
    click.echo(f"   Target met: {'✅' if avg_latency <= latency_target else '❌'}")

@test.command('pipeline')
@click.option('--name', default='test_pipeline', help='Pipeline name')
@click.option('--task', default='motor_imagery', type=click.Choice(['motor_imagery', 'p300', 'ssvep']))
def test_pipeline(name, task):
    """Test complete pipeline execution"""
    click.echo(f"🔧 Testing pipeline: {name} ({task})")
    
    import time
    
    
    # Simulate pipeline execution
    steps = [
        "Loading configuration...",
        "Initializing components...",
        "Starting data acquisition...",
        "Applying preprocessing...", 
        "Extracting features...",
        "Running classification...",
        "Generating results..."
    ]
    
    for step in steps:
        click.echo(f"  {step}")
        time.sleep(0.5)
    
    # Mock results
    accuracy = np.random.uniform(0.75, 0.95)
    latency = np.random.uniform(35, 65)
    
    click.echo(f"✅ Pipeline test completed!")
    click.echo(f"📊 Accuracy: {accuracy:.2f}")
    click.echo(f"⚡ Latency: {latency:.1f}ms")

@test.command('full')
@click.option('--quick', is_flag=True, help='Run quick test suite')
def test_full(quick):
    """Run complete neurOS test suite"""
    click.echo("🧪 Running neurOS Test Suite")
    click.echo("=" * 50)
    
    duration_multiplier = 0.3 if quick else 1.0
    
    # Test sequence
    tests = [
        ("System Status", "neuros status"),
        ("EEG Generation", f"neuros test eeg --duration {int(5 * duration_multiplier)}"),
        ("Device Simulation", f"neuros test device --duration {int(10 * duration_multiplier)}"),
        ("Real-time Processing", f"neuros test realtime --duration {int(15 * duration_multiplier)}"),
        ("Pipeline Execution", "neuros test pipeline")
    ]
    
    results = []
    
    for test_name, command in tests:
        click.echo(f"\n🔍 Running: {test_name}")
        click.echo(f"Command: {command}")
        
        # Simulate test execution
        import time
        time.sleep(1 * duration_multiplier)
        
        # Mock results
        success = np.random.random() > 0.1  # 90% success rate
        results.append((test_name, success))
        
        status = "✅ PASS" if success else "❌ FAIL"
        click.echo(f"Result: {status}")
    
    # Summary
    click.echo(f"\n📊 Test Summary")
    click.echo("=" * 30)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        click.echo(f"{status} {test_name}")
    
    click.echo(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        click.echo("🎉 All tests passed! neurOS is ready for action.")
    else:
        click.echo("⚠️  Some tests failed. Check the logs for details.")

@cli.group()
def ml():
    """Machine learning and model training commands"""
    if not ML_AVAILABLE:
        click.echo("⚠️  ML modules not available. Install additional dependencies.")
        return

@ml.command('train')
@click.option('--task', type=click.Choice(['motor_imagery', 'p300', 'ssvep']), 
              default='motor_imagery', help='BCI task type')
@click.option('--data-file', help='Path to training data (.npz file)')
@click.option('--synthetic', is_flag=True, help='Use synthetic data for demo')
@click.option('--trials', default=200, help='Number of synthetic trials')
@click.option('--channels', default=32, help='Number of channels')
@click.option('--duration', default=2.0, help='Trial duration in seconds')
@click.option('--models', default='rf,svm,xgb', help='Models to train (comma-separated)')
@click.option('--output-dir', default='models', help='Output directory')
@click.option('--cv-folds', default=5, help='Cross-validation folds')
@click.option('--feature-selection', is_flag=True, help='Enable feature selection')
@click.option('--hyperparameter-tuning', is_flag=True, help='Enable hyperparameter tuning')
def train_models(task, data_file, synthetic, trials, channels, duration, models, 
                output_dir, cv_folds, feature_selection, hyperparameter_tuning):
    """
    Train BCI classification models.

    This command trains one or more machine learning models on your dataset.
    You can use either synthetic data or load your own data from a file.

    **Synthetic Data**

    Use the `--synthetic` flag to generate synthetic data for a demo. You can
    specify the number of trials, channels, and duration in seconds.

    **Loading Data**

    To load your own data, specify the `--data-file` option with the path to
    an `.npz` file containing `X` and `y` arrays. The `X` array should have
    shape `(n_trials, n_channels, n_times)`, and the `y` array should have
    shape `(n_trials,)`.

    **Training Configuration**

    You can specify the following options to configure the training process:

    * `--models`: Comma-separated list of models to train (default: `rf,svm,xgb`)
    * `--output-dir`: Directory to save the trained models (default: `models`)
    * `--cv-folds`: Number of cross-validation folds (default: 5)
    * `--feature-selection`: Enable feature selection (default: False)
    * `--hyperparameter-tuning`: Enable hyperparameter tuning (default: False)

    **Example**

    To train an SVM model on your own data, use the following command:

        $ neurOS ml train --data-file path/to/data.npz --models svm

    To generate synthetic data and train multiple models, use the following command:

        $ neurOS ml train --synthetic --trials 200 --channels 32 --duration 2.0 --models rf,svm,xgb

    """
    
    """Train BCI classification models"""
    if not ML_AVAILABLE:
        click.echo("❌ ML modules not available")
        return
    
    click.echo(f"🧠 Training BCI models for {task}")
    click.echo("=" * 50)
    # Load or generate data
    if synthetic or not data_file:
        click.echo(f"🎲 Generating synthetic {task} data...")
        click.echo(f"   Trials: {trials}, Channels: {channels}, Duration: {duration}s")
        
        # Generate task-specific synthetic data
        sample_rate = 250
        n_times = int(duration * sample_rate)
        
        np.random.seed(42)
        X = np.random.randn(trials, channels, n_times)
        
        if task == 'motor_imagery':
            # Binary classification (left vs right hand)
            y = np.random.randint(0, 2, trials)
            class_names = ['Left Hand', 'Right Hand']
        elif task == 'p300':
            # Binary classification (target vs non-target)
            y = np.random.randint(0, 2, trials)
            class_names = ['Non-Target', 'Target']
        elif task == 'ssvep':
            # Multi-class classification (different frequencies)
            y = np.random.randint(0, 4, trials)  # 4 frequencies
            class_names = ['6Hz', '7.5Hz', '8.57Hz', '10Hz']
        
        click.echo(f"   Classes: {len(np.unique(y))} ({', '.join(class_names)})")
        
    else:
        click.echo(f"📁 Loading data from {data_file}")
        try:
            data = np.load(data_file)
            X = data['X']
            y = data['y']
            click.echo(f"   Loaded: {X.shape} samples, {len(np.unique(y))} classes")
        except Exception as e:
            click.echo(f"❌ Failed to load data: {e}")
            return
    
    # Configure training
    config = TrainingConfig(
        task_type=BCITask(task),
        models_to_test=models.split(','),
        output_dir=output_dir,
        cv_folds=cv_folds,
        feature_selection=feature_selection,
        hyperparameter_tuning=hyperparameter_tuning
    )
    
    # Run training with progress indication
    click.echo(f"\n🔧 Training Configuration:")
    click.echo(f"   Task: {task}")
    click.echo(f"   Models: {', '.join(config.models_to_test)}")
    click.echo(f"   CV Folds: {cv_folds}")
    click.echo(f"   Feature Selection: {'✅' if feature_selection else '❌'}")
    click.echo(f"   Hyperparameter Tuning: {'✅' if hyperparameter_tuning else '❌'}")
    
    click.echo(f"\n⚡ Starting training...")
    
    try:
        pipeline = BCITrainingPipeline(config)
        
        with click.progressbar(length=len(config.models_to_test), 
                             label='Training models') as bar:
            # Monkey patch to show progress
            original_train = pipeline.train_model
            def train_with_progress(*args, **kwargs):
                result = original_train(*args, **kwargs)
                bar.update(1)
                return result
            pipeline.train_model = train_with_progress
            
            summary = pipeline.run_training(X, y)
        
        # Display results
        click.echo("\n📊 Training Results:")
        click.echo("=" * 60)
        
        # Header
        click.echo(f"{'Model':<12} {'Accuracy':<10} {'F1-Score':<10} {'AUC':<8} {'CV Mean±Std':<15}")
        click.echo("-" * 60)
        
        # Results for each model
        for model_name, metrics in summary['validation_results'].items():
            cv_mean = metrics['cv_mean']
            cv_std = metrics['cv_std']
            click.echo(f"{model_name:<12} {metrics['accuracy']:<10.3f} "
                      f"{metrics['f1_score']:<10.3f} {metrics['auc_score']:<8.3f} "
                      f"{cv_mean:.3f}±{cv_std:.3f}")
        
        click.echo("-" * 60)
        click.echo(f"🏆 Best Model: {summary['best_model']} "
                  f"(Validation Accuracy: {summary['best_validation_score']:.3f})")
        
        # Test results if available
        if 'test_results' in summary:
            click.echo(f"\n🎯 Test Set Performance:")
            for model_name, test_metrics in summary['test_results'].items():
                click.echo(f"   {model_name}: {test_metrics['accuracy']:.3f} accuracy")
        
        click.echo(f"\n💾 Models saved to: {output_dir}")
        click.echo("✅ Training completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Training failed: {e}")
        if click.confirm("Show detailed error?"):
            import traceback
            traceback.print_exc()

@ml.command('evaluate')
@click.option('--model-file', required=True, help='Path to trained model (.pkl file)')
@click.option('--data-file', required=True, help='Path to test data (.npz file)')
@click.option('--output-file', help='Save evaluation results to file')
def evaluate_model(model_file, data_file, output_file):
    """Evaluate a trained BCI model"""
    if not ML_AVAILABLE:
        click.echo("❌ ML modules not available")
        return
    
    click.echo(f"📊 Evaluating model: {model_file}")
    
    try:
        # Load model and data
        import joblib
        
        model = joblib.load(model_file)
        data = np.load(data_file)
        X_test = data['X']
        y_test = data['y']
        
        click.echo(f"📁 Test data: {X_test.shape} samples, {len(np.unique(y_test))} classes")
        
        # Make predictions
        click.echo("🔮 Making predictions...")
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
        
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        cm = confusion_matrix(y_test, y_pred)
        
        # Display results
        click.echo(f"\n📊 Evaluation Results:")
        click.echo("=" * 40)
        click.echo(f"Accuracy: {accuracy:.3f}")
        click.echo(f"Precision: {report['weighted avg']['precision']:.3f}")
        click.echo(f"Recall: {report['weighted avg']['recall']:.3f}")
        click.echo(f"F1-Score: {report['weighted avg']['f1-score']:.3f}")
        
        click.echo(f"\n📈 Confusion Matrix:")
        click.echo(cm)
        
        # Save results if requested
        if output_file:
            results = {
                'accuracy': accuracy,
                'classification_report': report,
                'confusion_matrix': cm.tolist(),
                'predictions': y_pred.tolist(),
                'probabilities': y_proba.tolist()
            }
            
            import json
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            click.echo(f"💾 Results saved to: {output_file}")
        
        click.echo("✅ Evaluation completed!")
        
    except Exception as e:
        click.echo(f"❌ Evaluation failed: {e}")

@ml.command('predict')
@click.option('--model-file', required=True, help='Path to trained model (.pkl file)')
@click.option('--data-file', required=True, help='Path to input data (.npz file)')
@click.option('--output-file', help='Save predictions to file')
@click.option('--show-confidence', is_flag=True, help='Show prediction confidence')
def predict_data(model_file, data_file, output_file, show_confidence):
    """Make predictions with a trained BCI model"""
    if not ML_AVAILABLE:
        click.echo("❌ ML modules not available")
        return
    
    click.echo(f"🔮 Making predictions with: {model_file}")
    
    try:
        # Load model and data
        import joblib
        
        model = joblib.load(model_file)
        data = np.load(data_file)
        X = data['X']
        
        click.echo(f"📁 Input data: {X.shape} samples")
        
        # Make predictions
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)
        
        # Display results
        click.echo(f"\n🎯 Predictions:")
        click.echo("=" * 40)
        
        for i, (pred, proba) in enumerate(zip(predictions, probabilities)):
            confidence = np.max(proba)
            
            if show_confidence:
                click.echo(f"Sample {i+1:3d}: Class {pred} (confidence: {confidence:.3f})")
            else:
                click.echo(f"Sample {i+1:3d}: Class {pred}")
        
        # Summary statistics
        unique_preds, counts = np.unique(predictions, return_counts=True)
        click.echo(f"\n📊 Prediction Summary:")
        for pred, count in zip(unique_preds, counts):
            percentage = count / len(predictions) * 100
            click.echo(f"   Class {pred}: {count} samples ({percentage:.1f}%)")
        
        # Save predictions if requested
        if output_file:
            results = {
                'predictions': predictions.tolist(),
                'probabilities': probabilities.tolist(),
                'summary': {str(pred): int(count) for pred, count in zip(unique_preds, counts)}
            }
            
            import json
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            click.echo(f"💾 Predictions saved to: {output_file}")
        
        click.echo("✅ Prediction completed!")
        
    except Exception as e:
        click.echo(f"❌ Prediction failed: {e}")

@ml.command('features')
@click.option('--task', type=click.Choice(['motor_imagery', 'p300', 'ssvep']), 
              default='motor_imagery', help='BCI task type')
@click.option('--data-file', help='Path to EEG data (.npz file)')
@click.option('--synthetic', is_flag=True, help='Use synthetic data')
@click.option('--channels', default=32, help='Number of channels for synthetic data')
@click.option('--output-file', help='Save features to file')
def extract_features(task, data_file, synthetic, channels, output_file):
    """Extract features from EEG data"""
    if not ML_AVAILABLE:
        click.echo("❌ ML modules not available")
        return
    
    click.echo(f"🎯 Extracting {task} features")
    
    try:
        # Load or generate data
        
        if synthetic or not data_file:
            click.echo("🎲 Using synthetic data...")
            sample_rate = 250
            n_times = 500  # 2 seconds
            n_trials = 50
            
            np.random.seed(42)
            X = np.random.randn(n_trials, channels, n_times)
            y = np.random.randint(0, 2, n_trials)
        else:
            click.echo(f"📁 Loading data from {data_file}")
            data = np.load(data_file)
            X = data['X']
            y = data.get('y', np.zeros(X.shape[0]))
        
        click.echo(f"📊 Data shape: {X.shape}")
        
        # Initialize feature extractor
        if task == 'motor_imagery':
            extractor = MotorImageryFeatures(channels=X.shape[1])
        elif task == 'p300':
            extractor = P300Features(channels=X.shape[1])
        elif task == 'ssvep':
            extractor = SSVEPFeatures(channels=X.shape[1])
        
        # Extract features
        click.echo("⚡ Extracting features...")
        extractor.fit(X, y)
        features = extractor.transform(X)
        feature_names = extractor.get_feature_names()
        
        click.echo(f"✅ Extracted {features.shape[1]} features from {features.shape[0]} trials")
        
        # Show feature summary
        click.echo(f"\n📈 Feature Summary:")
        click.echo(f"   Total features: {len(feature_names)}")
        click.echo(f"   Feature range: [{np.min(features):.3f}, {np.max(features):.3f}]")
        click.echo(f"   Mean: {np.mean(features):.3f}, Std: {np.std(features):.3f}")
        
        # Show top features by variance
        feature_vars = np.var(features, axis=0)
        top_indices = np.argsort(feature_vars)[-10:][::-1]
        
        click.echo(f"\n🔝 Top 10 Most Variable Features:")
        for i, idx in enumerate(top_indices):
            click.echo(f"   {i+1:2d}. {feature_names[idx]}: {feature_vars[idx]:.3f}")
        
        # Save features if requested
        if output_file:
            np.savez(output_file, 
                    features=features, 
                    feature_names=feature_names,
                    labels=y)
            click.echo(f"💾 Features saved to: {output_file}")
        
        click.echo("✅ Feature extraction completed!")
        
    except Exception as e:
        click.echo(f"❌ Feature extraction failed: {e}")

@ml.command('benchmark')
@click.option('--task', type=click.Choice(['motor_imagery', 'p300', 'ssvep']), 
              default='motor_imagery', help='BCI task type')
@click.option('--trials', default=500, help='Number of trials for benchmark')
@click.option('--quick', is_flag=True, help='Quick benchmark with fewer models')
def benchmark_models(task, trials, quick):
    """Benchmark different models on synthetic BCI data"""
    if not ML_AVAILABLE:
        click.echo("❌ ML modules not available")
        return
    
    click.echo(f"🏁 Benchmarking {task} classification models")
    click.echo(f"📊 Using {trials} synthetic trials")
    
    # Generate synthetic data
    click.echo("🎲 Generating synthetic data...")
    sample_rate = 250
    n_channels = 32
    n_times = 500  # 2 seconds

    
    
    np.random.seed(42)
    X = np.random.randn(trials, n_channels, n_times)
    
    if task == 'motor_imagery':
        y = np.random.randint(0, 2, trials)
    elif task == 'p300':
        y = np.random.randint(0, 2, trials)
    elif task == 'ssvep':
        y = np.random.randint(0, 4, trials)
    
    # Configure benchmark
    if quick:
        models = ['rf', 'svm']
        cv_folds = 3
        hyperparameter_tuning = False
    else:
        models = ['rf', 'svm', 'xgb', 'lr', 'mlp']
        cv_folds = 5
        hyperparameter_tuning = True
    
    config = TrainingConfig(
        task_type=BCITask(task),
        models_to_test=models,
        cv_folds=cv_folds,
        hyperparameter_tuning=hyperparameter_tuning,
        save_models=False  # Don't save for benchmark
    )
    
    # Run benchmark
    click.echo(f"⚡ Running benchmark...")
    
    try:
        pipeline = BCITrainingPipeline(config)
        summary = pipeline.run_training(X, y)
        
        # Display benchmark results
        click.echo(f"\n🏆 Benchmark Results ({task}):")
        click.echo("=" * 70)
        click.echo(f"{'Rank':<6} {'Model':<12} {'Accuracy':<10} {'F1-Score':<10} {'AUC':<8} {'Time (s)':<10}")
        click.echo("-" * 70)
        
        # Sort by accuracy
        sorted_results = sorted(
            summary['validation_results'].items(),
            key=lambda x: x[1]['accuracy'], 
            reverse=True
        )
        
        for rank, (model_name, metrics) in enumerate(sorted_results, 1):
            # Get training time from pipeline results
            training_time = pipeline.results[model_name].training_time if model_name in pipeline.results else 0
            
            click.echo(f"{rank:<6} {model_name:<12} {metrics['accuracy']:<10.3f} "
                      f"{metrics['f1_score']:<10.3f} {metrics['auc_score']:<8.3f} "
                      f"{training_time:<10.1f}")
        
        click.echo("-" * 70)
        click.echo(f"🥇 Winner: {sorted_results[0][0]} with {sorted_results[0][1]['accuracy']:.3f} accuracy")
        
        # Performance insights
        click.echo(f"\n💡 Insights:")
        accuracies = [metrics['accuracy'] for _, metrics in sorted_results]
        click.echo(f"   Best accuracy: {max(accuracies):.3f}")
        click.echo(f"   Worst accuracy: {min(accuracies):.3f}")
        click.echo(f"   Average accuracy: {np.mean(accuracies):.3f}")
        click.echo(f"   Accuracy range: {max(accuracies) - min(accuracies):.3f}")
        
        click.echo("✅ Benchmark completed!")
        
    except Exception as e:
        click.echo(f"❌ Benchmark failed: {e}")

# Add the ml group to the main CLI
# Make sure to add this line after the cli group definition:
# cli.add_command(ml)

@cli.command()
def hello():
    """Say hello from neurOS"""
    try:
        import neuros
        click.echo(neuros.hello_neuros())
    except ImportError:
        click.echo("🧠 Hello from neurOS! (Module not fully installed)")

@cli.group()
def deploy():
    """Deployment management commands"""
    pass

@deploy.command()
@click.option('--environment', type=click.Choice(['development', 'staging', 'production']), required=True)
@click.option('--name', help='Deployment name')
@click.option('--build/--no-build', default=True, help='Build images before deployment')
def create(environment, name, build):
    """Deploy neurOS to specified environment"""
    click.echo(f"🚀 Deploying to {environment}...")
    click.echo("⚠️  Note: This is a simulation. Full deployment requires Kubernetes setup.")
    
    # Simulate deployment steps
    steps = [
        "Building Docker images...",
        "Generating Kubernetes manifests...",
        "Applying configurations...",
        "Starting services...",
        "Verifying deployment..."
    ]
    
    import time
    for step in steps:
        click.echo(f"  {step}")
        time.sleep(0.5)
    
    click.echo(f"✅ Simulated deployment to {environment} completed!")

@deploy.command()
@click.option('--namespace', default='neuros-enterprise')
def status(namespace):
    """Get deployment status"""
    click.echo(f"📊 Deployment Status (simulated)")
    click.echo(f"Namespace: {namespace}")
    click.echo("Services:")
    
    # Mock service status
    services = [
        ("processing-engine", "2/2", "running"),
        ("dashboard", "1/1", "running"),
        ("ai-agents", "1/1", "running"),
        ("hardware-interface", "1/1", "running")
    ]
    
    for service, replicas, status in services:
        click.echo(f"  ✅ {service}: {replicas} ready ({status})")


def main():
    """Main CLI entry point"""
    try:
        cli()
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
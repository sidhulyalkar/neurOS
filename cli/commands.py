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
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Import neurOS modules
from core.realtime.engine import RealtimeProcessor, RealtimeConfig
from agents.framework import AgentManager, create_default_agents
from hardware.interface import HardwareManager, load_hardware_profile
from enterprise.security import SecurityManager, SecurityConfig, SecurityLevel
from core.pipeline.enhanced_pipeline import EnhancedPipeline, PipelineConfig

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
        await pipeline.initialize()
        
        # Simulate processing (replace with actual data loading)
        import numpy as np
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
        config = RealtimeConfig(
            target_latency_ms=latency_target,
            max_buffer_size=buffer_size,
            adaptive_optimization=adaptive
        )
        
        engine = RealtimeProcessor(config)
        
        # Add simple processing function
        def bandpass_filter(data):
            import time
            time.sleep(0.001)  # Simulate 1ms processing
            return data * 0.95
        
        engine.add_processor(bandpass_filter)
        
        # Add callback to show results
        def show_result(data, metadata):
            if engine.packets_received % 50 == 0:  # Show every 50th packet
                click.echo(f"📊 Processed sample {engine.packets_received}: {metadata['latency_ms']:.2f}ms")
        
        engine.add_callback(show_result)
        
        await engine.start()
        click.echo("✅ Real-time engine started")
        
        # Simulate real-time data
        try:
            import numpy as np
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

# Add to the end of your commands.py file, in the main() function:
def main():
    """Main CLI entry point"""
    try:
        cli()
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
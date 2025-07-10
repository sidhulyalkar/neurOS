#!/usr/bin/env python3
"""
neurOS Command Line Interface
"""

import click
import asyncio
import os
import sys
from pathlib import Path

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """neurOS - The Operating System for Brain-Computer Interfaces"""
    pass

@cli.command()
def status():
    """Show neurOS system status"""
    click.echo("🔍 neurOS System Status")
    click.echo("=" * 40)
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    click.echo(f"Python Version: {python_version}")
    
    # Check dependencies
    try:
        import numpy
        click.echo(f"✅ NumPy: {numpy.__version__}")
    except ImportError:
        click.echo("❌ NumPy: Not installed")
    
    try:
        import streamlit
        click.echo(f"✅ Streamlit: {streamlit.__version__}")
    except ImportError:
        click.echo("❌ Streamlit: Not installed")

@cli.command()
@click.option('--port', default=8501, help='Dashboard port')
def dashboard(port):
    """Launch the neurOS dashboard"""
    click.echo(f"🚀 Starting neurOS dashboard at http://localhost:{port}")
    import subprocess
    subprocess.run([
        'streamlit', 'run', 'frontend/enhanced_dashboard.py',
        '--server.port', str(port)
    ])

def main():
    """Main CLI entry point"""
    cli()

if __name__ == '__main__':
    main()

# setup.py
"""
neurOS - The Operating System for Brain-Computer Interfaces
Enterprise-grade BCI development, deployment, and management platform
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="neuros",
    version="1.0.0",
    description="The Operating System for Brain-Computer Interfaces",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sidharth Hulyalkar",
    author_email="sid.soccer.21@gmail.com",
    url="https://github.com/sidhulyalkar/neurOS",
    project_urls={
        "Documentation": "https://docs.neuros.ai",
        "Source": "https://github.com/sidhulyalkar/neurOS",
        "Tracker": "https://github.com/sidhulyalkar/neurOS/issues",
    },
    packages=find_packages(),
    python_requires=">=3.10",
    
    # Core dependencies
    install_requires=[
        # Web framework and API
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "aiofiles>=23.2.1",
        
        # Data processing and ML
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        
        # Visualization and dashboard
        "streamlit>=1.28.0",
        "plotly>=5.17.0",
        "matplotlib>=3.7.0",
        
        # Data validation and serialization
        "pydantic>=2.5.0",
        "PyYAML>=6.0.1",
        
        # CLI and utilities
        "click>=8.1.0",
        "rich>=13.6.0",
        "typer>=0.9.0",
        
        # Async and concurrency
        "asyncio-mqtt>=0.13.0",
        "aioredis>=2.0.1",
        
        # System monitoring
        "psutil>=5.9.0",
        
        # Security and authentication
        "bcrypt>=4.1.0",
        "passlib[bcrypt]>=1.7.4",
        "python-jose[cryptography]>=3.3.0",
        "python-multipart>=0.0.6",
        
        # Date and time handling
        "python-dateutil>=2.8.2",
        
        # Configuration management
        "python-dotenv>=1.0.0",
    ],
    
    # Optional dependencies
    extras_require={
        # GPU support
        "gpu": [
            "GPUtil>=1.4.0",
            "torch>=2.0.0",
            "tensorflow>=2.13.0",
        ],
        
        # Container orchestration
        "orchestration": [
            "docker>=6.1.0",
            "kubernetes>=28.1.0",
        ],
        
        # Database support
        "database": [
            "redis>=5.0.0",
            "sqlalchemy>=2.0.0",
            "alembic>=1.12.0",
            "asyncpg>=0.29.0",
        ],
        
        # Cloud providers
        "cloud": [
            "boto3>=1.34.0",
            "azure-storage-blob>=12.19.0",
            "google-cloud-storage>=2.10.0",
        ],
        
        # Development tools
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.9.0",
            "flake8>=6.1.0",
            "mypy>=1.6.0",
            "pre-commit>=3.5.0",
        ],
        
        # Documentation
        "docs": [
            "sphinx>=7.2.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
            "sphinx-autodoc-typehints>=1.25.0",
        ],
        
        # Testing and validation
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "httpx>=0.25.0",
            "factory-boy>=3.3.0",
        ],
        
        # All optional dependencies
        "all": [
            "GPUtil>=1.4.0",
            "torch>=2.0.0",
            "docker>=6.1.0",
            "kubernetes>=28.1.0",
            "redis>=5.0.0",
            "boto3>=1.34.0",
            "pytest>=7.4.0",
            "black>=23.9.0",
            "sphinx>=7.2.0",
        ],
    },
    
    # Entry points for CLI
    entry_points={
        "console_scripts": [
            "neuros=cli.main:main",
        ],
    },
    
    # Package data
    include_package_data=True,
    package_data={
        "neuros": [
            "config/*.yaml",
            "templates/*.html",
            "static/*",
        ],
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Operating System",
        "Typing :: Typed",
    ],
    
    # Keywords
    keywords=[
        "bci", "brain-computer-interface", "neuroscience", "eeg", "ecog",
        "machine-learning", "real-time", "signal-processing", "neurotechnology",
        "operating-system", "enterprise", "collaboration", "edge-computing",
        "distributed-computing", "cloud-computing", "distributed-systems",
        "containerization", "orchestration","auto-scaling", "database",
        "cloud", "neuros", "neurOS", "dashboard", "agents", "cli", "deep learning"
    ],
    
    # Minimum Python version check
    zip_safe=False,
)
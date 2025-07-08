# setup.py
from setuptools import setup, find_packages

# Merge existing NeuroForge requirements: e.g., numpy, scipy, pandas, mne, scikit-learn, etc.
requirements = [
    "openai",
    "pyyaml",
    "numpy",
    "pandas",
    "scipy",
    "streamlit",
    "pytest",
    "brainflow",
    "fastapi",
    "plotly", 
    "coverage",
    "matplotlib",
    "scikit-learn",
    "data-repository",
    "deltalake",
    "polars",
    "streamlit-aggrid",
    "click"
]

setup(
    name="neurOS",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        *requirements,
    ],
    entry_points={
        "console_scripts": [
            "neuros=middleware.interfaces.cli:cli",
            "neuros-orchestrator=core.orchestrator.main:main",
        ],
    },
)
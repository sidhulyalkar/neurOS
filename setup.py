from setuptools import setup, find_packages
import os

# Read README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
requirements_file = "requirements.txt"
if os.path.exists(requirements_file):
    with open(requirements_file, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
else:
    # Fallback requirements if file doesn't exist
    requirements = [
        "click>=8.0.0",
        "asyncio",
        "pyyaml>=6.0",
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "streamlit>=1.28.0",
        "plotly>=5.0.0",
        "pandas>=1.3.0",
        "cryptography>=3.4.0",
        "pyjwt>=2.4.0",
        "prometheus-client>=0.14.0",
        "psutil>=5.8.0",
    ]

setup(
    name="neuros",
    version="1.0.1",
    author="Sidharth Hulyalkar",
    author_email="sidsoccer21@gmail.com",
    project_url="https://github.com/sidhulyalkar/neurOS",
    description="The Operating System for Brain-Computer Interfaces",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "neuros=cli.commands:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    include_package_data=True,
    package_data={
        "neuros": ["*.yaml", "*.yml", "*.json"],
    },
)
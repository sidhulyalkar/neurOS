# Dockerfile for NeurOS
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY frontend/ ./frontend
COPY infra/ ./infra
COPY middleware/ ./middleware
COPY hardware_profiles/ ./hardware_profiles
COPY mock_data/ ./mock_data
COPY agents/ ./agents
COPY core/ ./core
COPY tests/ ./tests
COPY testing/ ./testing
COPY api/ ./api
COPY cli/ ./cli
COPY collaboration/ ./collaboration
COPY apps/ ./apps
COPY workflows/ ./workflows
COPY enterprise/ ./enterprise

COPY edge/ ./edge
COPY enterprise/ ./enterprise
COPY pipeline/ ./pipeline
COPY utils/ ./utils
COPY scripts/ ./scripts

# Install Streamlit
RUN pip install streamlit    
RUN pip install streamlit_authenticator 
RUN pip install streamlit_extras        
RUN pip install streamlit_option_menu       

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Copy files    
COPY requirements.txt .
COPY pipeline.py .
COPY README.md .
COPY setup.py .



# Run the Streamlit dashboard
CMD ["streamlit", "run", "frontend/dashboard.py"]
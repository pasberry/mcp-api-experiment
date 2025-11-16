# Docker image for sandboxed code execution
FROM python:3.11-slim

# Install dependencies
RUN pip install --no-cache-dir \
    mcp>=0.1.0 \
    httpx>=0.25.0

# Create workspace
WORKDIR /workspace

# Copy framework code (will be overridden by volume mount in development)
COPY src/mcp_skill_framework /opt/mcp_skill_framework

# Add framework to Python path
ENV PYTHONPATH=/opt:/workspace/src:${PYTHONPATH}

# Default command (will be overridden)
CMD ["python", "-c", "print('Container ready')"]

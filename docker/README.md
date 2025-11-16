# Docker Sandbox Environment

This directory contains the Docker configuration for sandboxed code execution.

## Overview

The Docker container provides:
- **Isolation**: Code runs in a separate container
- **Resource limits**: CPU and memory constraints
- **Security**: Prevents access to host system
- **Clean environment**: Consistent Python environment

## How It Works

1. **Build**: The Docker image is built automatically on first use
2. **Execute**: Code runs in a fresh container with mounted volumes
3. **Cleanup**: Container is removed after execution

## Volume Mounts

The container has access to:
- `/workspace/src` - Framework source code (read-only)
- `/workspace/servers` - Generated MCP APIs (read-only)
- `/workspace/skills` - Agent skills (read-write)
- `/workspace/tasks` - Task checkpoints (read-write)
- `/workspace/tmp` - Temporary files (read-write)

## Resource Limits

Default limits:
- **Memory**: 512MB
- **CPU**: 50% of one CPU core
- **Network**: Host network mode (to access MCP servers)

## Manual Build

To manually build the image:

```bash
cd /path/to/mcp-api-experiment
docker build -f docker/Dockerfile -t mcp-skill-framework-executor:latest .
```

## Testing

To test the image:

```bash
docker run --rm -v $(pwd)/src:/workspace/src mcp-skill-framework-executor:latest python -c "import mcp_skill_framework; print('OK')"
```

## Fallback

If Docker is not available, the framework automatically falls back to subprocess execution.

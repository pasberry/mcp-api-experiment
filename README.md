# MCP Skill Framework

A framework for building agents with MCP through code execution and skill accumulation.

## Overview

The MCP Skill Framework converts MCP (Model Context Protocol) tools into domain-specific Python APIs that agents can compose to solve arbitrary problems. Instead of exposing agents to MCP tool schemas (which consume excessive context), this framework:

1. **Connects to MCP servers** as a client
2. **Generates clean Python APIs** that hide MCP details
3. **Enables agents to write code** using these APIs
4. **Persists solutions as skills** that accumulate over time
5. **Supports checkpointing** for long-running tasks

## Key Benefits

- **Massive token reduction**: Agents see Python APIs, not verbose tool schemas
- **Progressive disclosure**: Agents explore APIs on-demand via filesystem
- **Skill accumulation**: Agents get smarter by composing and reusing solutions
- **Code-based state**: Checkpoints are human-readable Python code
- **Framework agnostic**: Works with any agent framework (LangGraph, CrewAI, etc.)

## Architecture

```
MCP Servers (Google Drive, Salesforce, etc.)
        ↓ MCP Protocol
Framework (generates Python APIs)
        ↓
servers/  (domain-specific APIs)
        ↓
Agent     (composes solutions)
        ↓
skills/   (accumulated knowledge)
```

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from mcp_skill_framework import Framework

# Initialize framework
framework = Framework(
    servers_dir="servers",
    skills_dir="skills",
    tasks_dir="tasks"
)

# Register MCP servers
framework.add_mcp_server(
    name="filesystem",
    command="npx -y @modelcontextprotocol/server-filesystem /tmp"
)

# Generate Python APIs from MCP tools
framework.generate_apis()

# Start runtime
framework.start()

# Agent writes code using generated APIs
agent_code = """
from servers.filesystem.read_file import execute as read_file

content = read_file("/tmp/example.txt")
print(f"File contains {len(content)} characters")
"""

# Execute and optionally save as skill
result = framework.execute(
    code=agent_code,
    save_as_skill="read_and_count",
    category="file_operations"
)

# Cleanup
framework.stop()
```

## Directory Structure

```
mcp-skill-framework/
├── src/mcp_skill_framework/  # Framework source code
├── servers/                  # Generated APIs (e.g., servers/google_drive/list_files/)
├── skills/                   # Agent-accumulated skills
├── tasks/                    # Task checkpoints
└── examples/                 # Example usage
```

## Development Status

This project is in active development. See implementation plan for details.

## License

MIT

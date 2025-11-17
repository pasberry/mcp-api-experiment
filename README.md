# MCP Skill Framework

A code generation and skill persistence framework for building agents with MCP.

## Overview

The MCP Skill Framework converts MCP (Model Context Protocol) tools into domain-specific Python APIs and provides persistent skill storage for agents. Instead of exposing agents to verbose MCP tool schemas, this framework:

1. **Generates clean Python APIs** from MCP server configurations
2. **Enables agents to write reusable code** using these APIs
3. **Persists skills to SQLite database** for cross-session knowledge retention
4. **Hydrates skills on startup** so agents can immediately use accumulated knowledge
5. **Supports multi-agent isolation** with agent-specific skill namespaces

## Key Benefits

- **Massive token reduction**: Agents see Python APIs, not verbose tool schemas
- **Progressive disclosure**: Agents explore APIs on-demand via filesystem
- **Skill accumulation**: Agents build knowledge over time by saving working code
- **Database persistence**: Skills survive agent restarts and container rebuilds
- **Multi-agent support**: Multiple agents can share one database with isolated skills
- **Framework agnostic**: Works with any agent framework (LangGraph, CrewAI, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Developer Workflow (One-time)                               │
├─────────────────────────────────────────────────────────────┤
│ 1. Configure MCP servers                                    │
│ 2. Run code generation                                      │
│ 3. Commit servers/ package to git                           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Agent Runtime (Every session)                               │
├─────────────────────────────────────────────────────────────┤
│ 1. Hydrate skills from database → skills/                  │
│ 2. Import generated APIs from servers/                     │
│ 3. Import existing skills from skills/                     │
│ 4. Create new skills → save to skills/ + persist to DB     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Storage                                                      │
├─────────────────────────────────────────────────────────────┤
│ • servers/        → Git (committed with agent code)         │
│ • skills/         → Ephemeral (regenerated from DB)         │
│ • skills.db       → SQLite (source of truth for skills)     │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from mcp_skill_framework import MCPApi

async def main():
    # Initialize API with agent name (required)
    api = MCPApi(
        agent_name="my-agent",
        servers_dir="servers",
        skills_dir="skills",
        skills_db="skills.db"
    )

    # === ONE-TIME: Code Generation ===
    # Register MCP servers
    api.add_mcp_server(
        name="filesystem",
        command="npx -y @modelcontextprotocol/server-filesystem /tmp"
    )

    # Generate Python libraries from MCP tools
    api.generate_libraries()
    # → Creates servers/filesystem/ package
    # → Commit servers/ to git with your agent code

    # === EVERY SESSION: Hydrate Skills ===
    # Restore skills from database
    count = await api.hydrate_skills()
    print(f"Loaded {count} skills from previous sessions")

    # Start MCP runtime
    api.start()

    # === AGENT CREATES NEW SKILLS ===
    # Agent writes code using generated APIs
    skill_code = '''
from servers.filesystem.read_file import read_file

def count_lines(filepath):
    """Count lines in a file."""
    content = read_file(filepath)
    return len(content.split('\\n'))
'''

    # Save as skill (immediately available + persisted to DB)
    api.save_skill(
        code=skill_code,
        name="count_lines",
        category="file_operations",
        tags=["filesystem", "utility"]
    )

    # List all skills
    skills = api.list_skills()
    print(f"Total skills: {len(skills)}")

    # Get database stats
    stats = await api.get_skill_stats()
    print(f"Skills in database: {stats['total_skills']}")

    # Cleanup
    api.stop()

asyncio.run(main())
```

## Core Concepts

### 1. Code Generation

The framework generates Python wrapper functions for each MCP tool:

```python
# MCP tool schema (verbose, many tokens)
{
  "name": "list_files",
  "description": "List files in directory",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string"}
    }
  }
}

# Generated Python API (clean, few tokens)
def list_files(path: str) -> dict:
    """List files in directory."""
    return mcp_call('google_drive', 'list_files', {'path': path})
```

Generated APIs are saved to `servers/{server_name}/{tool_name}/main.py`.

### 2. Skill Persistence

When agents save skills:

1. **Immediately written to filesystem** (`skills/{category}/{name}/`)
   - Agent can import and use right away
   - Includes main.py, README.md, metadata

2. **Asynchronously persisted to database**
   - SQLite database with (agent_name, skill_name) as key
   - Survives container restarts and agent sessions

3. **Hydration on startup**
   - Database is source of truth
   - Clears and rebuilds `skills/` directory from DB
   - Ensures consistency across sessions

### 3. Multi-Agent Support

Multiple agents can share one database:

```python
# Agent 1
api1 = MCPApi(agent_name="agent-1", skills_db="shared.db")
api1.save_skill(code, "skill1", "category1")

# Agent 2
api2 = MCPApi(agent_name="agent-2", skills_db="shared.db")
api2.save_skill(code, "skill2", "category2")

# Isolated: agent-1 only sees skill1, agent-2 only sees skill2
```

## Directory Structure

```
your-agent-project/
├── servers/              # Generated MCP APIs (commit to git)
│   ├── filesystem/
│   │   ├── read_file/
│   │   │   ├── main.py
│   │   │   └── README.md
│   │   └── write_file/
│   └── google_drive/
│
├── skills/               # Agent skills (ephemeral, from DB)
│   ├── file_operations/
│   │   ├── count_lines/
│   │   │   ├── main.py
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   └── .meta.json
│   │   └── get_file_size/
│   └── data_processing/
│
├── skills.db             # SQLite database (source of truth)
│
└── your_agent.py         # Your agent code
```

## API Reference

### MCPApi

```python
api = MCPApi(
    agent_name: str,                    # Required: Agent identifier
    servers_dir: str = "servers",       # Generated API directory
    skills_dir: str = "skills",         # Skills directory
    skills_db: str = "skills.db",       # SQLite database path
    telemetry_db: Optional[str] = ...   # Telemetry database (optional)
)
```

### Methods

**Code Generation**
- `add_mcp_server(name, command)` - Register an MCP server
- `generate_libraries()` - Generate Python APIs from all servers

**Runtime Management**
- `start()` - Connect to MCP servers
- `stop()` - Disconnect from MCP servers

**Skill Management**
- `save_skill(code, name, category, tags=None, persist_to_db=True)` - Save a skill
- `list_skills(category=None)` - List skills from filesystem
- `get_skill_info(category, name)` - Get detailed skill information
- `await hydrate_skills()` - Restore skills from database (async)
- `await get_skill_stats()` - Get database statistics (async)

## Examples

See the `examples/` directory:

- **basic_usage.py** - Complete workflow walkthrough
- **skill_persistence_demo.py** - Demonstrates hydration and multi-agent support

Run examples:
```bash
python examples/basic_usage.py
python examples/skill_persistence_demo.py
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=mcp_skill_framework --cov-report=html
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Use Cases

This framework is ideal for:

- **Autonomous agents** that need to accumulate knowledge over time
- **Multi-session workflows** where skills should persist across restarts
- **Multi-agent systems** with shared skill databases
- **Tool-heavy agents** that benefit from clean API wrappers
- **Development teams** that want to commit generated code to git

## Design Decisions

**Why database persistence?**
- Skills survive container restarts and agent crashes
- Enables multi-agent knowledge sharing
- Provides queryable skill metadata
- Supports future features (skill versioning, analytics)

**Why immediate filesystem + async DB?**
- Agent can use skill immediately (no waiting for DB write)
- Non-blocking persistence keeps agent responsive
- Filesystem serves as working directory
- Database serves as durable source of truth

**Why clear and rebuild on hydration?**
- Database is single source of truth (no sync conflicts)
- Simple, predictable behavior
- Ensures consistency across sessions

## Comparison to MCP Direct Usage

| Aspect | MCP Direct | This Framework |
|--------|-----------|----------------|
| Context usage | ~500 tokens/tool | ~50 tokens/tool |
| Agent interface | JSON schemas | Python functions |
| Skill persistence | None | SQLite database |
| Multi-session | No memory | Hydrates from DB |
| Discovery | Browse all schemas | Explore filesystem |
| Type safety | JSON validation | Python type hints |

## Contributing

Contributions are welcome! Please ensure:
- Tests pass: `pytest tests/`
- Code is formatted: `black src/ tests/`
- Types are correct: `mypy src/`

## License

MIT

## Acknowledgments

Built on top of [Model Context Protocol (MCP)](https://modelcontextprotocol.io) by Anthropic.

Inspired by the article: [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

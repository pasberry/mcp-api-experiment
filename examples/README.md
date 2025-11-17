# MCP Skill Framework Examples

This directory contains examples demonstrating the MCP Skill Framework.

## Prerequisites

1. Install the framework:
   ```bash
   pip install -e .
   ```

2. Install Node.js and npx (for MCP servers)

3. Install an MCP server (e.g., filesystem):
   ```bash
   npx @modelcontextprotocol/server-filesystem
   ```

## Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates the complete workflow:
- Code generation from MCP servers
- Skill hydration from database
- Creating and saving skills
- Database persistence

**Run:**
```bash
python examples/basic_usage.py
```

**What it does:**
1. Registers MCP filesystem server
2. Generates Python APIs in `servers/filesystem/`
3. Hydrates existing skills from database
4. Creates new skills and persists them
5. Shows database statistics

### 2. Skill Persistence Demo (`skill_persistence_demo.py`)

Demonstrates:
- Creating skills across multiple sessions
- Skill hydration on agent restart
- Multi-agent isolation with shared database

**Run:**
```bash
python examples/skill_persistence_demo.py
```

**What it does:**
1. **Session 1**: Agent creates skills and persists to database
2. **Session 2**: Simulates restart and hydrates skills from DB
3. **Session 3**: Shows multi-agent isolation using same database

## Generated Output

After running the examples, you'll see:

```
your-project/
├── servers/              # Generated Python APIs (commit to git)
│   └── filesystem/
│       ├── read_file/
│       │   ├── main.py
│       │   ├── README.md
│       │   └── __init__.py
│       └── ...
├── skills/               # Agent skills (ephemeral, from DB)
│   └── file_operations/
│       └── count_lines/
│           ├── main.py
│           ├── README.md
│           ├── __init__.py
│           └── .meta.json
└── skills.db             # SQLite database (source of truth)
```

## Key Concepts

### Code Generation

Generated APIs provide clean wrappers around MCP tools:

```python
# Generated in servers/filesystem/read_file/main.py
from mcp_skill_framework.runtime import mcp_call

def filesystem_read_file(path: str) -> dict:
    """Read contents of a file."""
    return mcp_call('filesystem', 'read_file', {'path': path})
```

### Skill Persistence

Skills are stored in two places:
1. **Filesystem** (`skills/`) - Immediately available for imports
2. **Database** (`skills.db`) - Source of truth, survives restarts

### Hydration Workflow

```python
# On agent startup
api = MCPApi(agent_name="my-agent", skills_db="skills.db")

# Restore skills from database
count = await api.hydrate_skills()  # Rebuilds skills/ from DB

# Now agent can import existing skills
from skills.data_processing.analyze import analyze
```

## Using Skills

Once skills are created, they can be imported like any Python module:

```python
# Agent creates a skill
skill_code = '''
def process_data(items):
    """Process a list of items."""
    return [item.upper() for item in items]
'''

api.save_skill(skill_code, "process_data", "data_processing")

# Later, agent (or another agent) can use it
from skills.data_processing.process_data import process_data

result = process_data(["hello", "world"])
```

## Progressive Disclosure

Agents can explore APIs by reading README files:

```bash
# Agent reads directory structure
ls servers/filesystem/

# Agent reads specific tool documentation
cat servers/filesystem/read_file/README.md

# Agent decides which tools to use
# Then imports only what's needed
```

This dramatically reduces token usage compared to loading all tool schemas upfront.

## Multi-Agent Support

Multiple agents can share one database:

```python
# Agent 1
api1 = MCPApi(agent_name="agent-1", skills_db="shared.db")
api1.save_skill(code, "skill1", "category1")

# Agent 2
api2 = MCPApi(agent_name="agent-2", skills_db="shared.db")
api2.save_skill(code, "skill2", "category2")

# Each agent only sees their own skills
await api1.hydrate_skills()  # Gets skill1 only
await api2.hydrate_skills()  # Gets skill2 only
```

## Tips

1. **Commit `servers/` to git**: Generated APIs are stable and should be versioned with your agent code

2. **Don't commit `skills/`**: Skills directory is ephemeral, regenerated from database

3. **Backup `skills.db`**: This is your agent's accumulated knowledge

4. **Use tags**: Tag skills for better organization and discovery

5. **Iterate on skills**: Skills can be overwritten to improve them over time

## Next Steps

Build your own agent that:
1. Generates APIs from MCP servers
2. Hydrates skills on startup
3. Creates new skills as it solves problems
4. Accumulates knowledge in the database

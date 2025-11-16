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
   npm install -g @modelcontextprotocol/server-filesystem
   ```

## Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates:
- Connecting to an MCP server
- Generating Python APIs
- Executing agent code
- Saving skills

**Run:**
```bash
python examples/basic_usage.py
```

**What it does:**
1. Connects to the filesystem MCP server
2. Generates Python APIs in `servers/filesystem/`
3. Executes code that uses those APIs
4. Saves reusable code as a skill in `skills/`

### 2. Checkpoint Demo (`checkpoint_demo.py`)

Demonstrates:
- Creating task checkpoints
- Saving state as Python code
- Resuming from checkpoints

**Run:**
```bash
python examples/checkpoint_demo.py
```

**What it does:**
1. Creates a checkpoint for a long-running task
2. Serializes task state as Python code
3. Demonstrates resuming from that checkpoint

## Generated Output

After running the examples, you'll see:

```
mcp-api-experiment/
├── servers/           # Generated APIs
│   └── filesystem/
│       ├── read_file/
│       │   ├── main.py
│       │   ├── README.md
│       │   └── __init__.py
│       └── ...
├── skills/            # Accumulated skills
│   └── file_operations/
│       └── count_lines/
│           ├── main.py
│           ├── README.md
│           ├── __init__.py
│           └── .meta.json
└── tasks/             # Checkpoints
    └── file_processing_20251116/
        ├── checkpoint.py
        ├── README.md
        └── .meta.json
```

## Exploring Generated APIs

After generating APIs, you can explore them:

```bash
# List generated APIs
ls -la servers/

# Read an API description
cat servers/filesystem/read_file/README.md

# Read generated Python code
cat servers/filesystem/read_file/main.py
```

## Using Skills

Once skills are created, they can be imported and reused:

```python
from skills.file_operations.count_lines import count_lines

num_lines = count_lines("/path/to/file.txt")
print(f"File has {num_lines} lines")
```

## Tips

1. **Progressive Disclosure**: Agents can explore `servers/` by reading README files to decide which APIs to use

2. **Skill Accumulation**: Over time, `skills/` grows with reusable patterns

3. **Checkpointing**: Long-running tasks can be checkpointed and resumed

4. **Token Efficiency**: Agents see clean Python code instead of verbose MCP tool schemas

## Next Steps

Try building your own agent that:
1. Explores available APIs
2. Writes code to solve problems
3. Accumulates skills over time
4. Uses checkpointing for complex tasks

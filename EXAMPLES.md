# Examples Guide - How They Work

This guide provides a deep dive into how the MCP Skill Framework examples work, explaining every step of the execution flow.

## Table of Contents

1. [Example 1: Basic Usage](#example-1-basic-usage)
2. [Example 2: Checkpoint Demo](#example-2-checkpoint-demo)
3. [Real-World Usage Patterns](#real-world-usage-patterns)

---

## Example 1: Basic Usage

**File:** `examples/basic_usage.py`

This demonstrates the core workflow: connecting to MCP, generating APIs, executing code, and saving skills.

### Step-by-Step Breakdown

#### 1. Initialization

```python
api = MCPApi(
    servers_dir="servers",
    skills_dir="skills",
    tasks_dir="tasks"
)
```

**What happens:**
- Creates three directories: `servers/`, `skills/`, `tasks/`
- Initializes all components (MCPConnector, MCPRuntime, CodeExecutor, etc.)
- Tries to initialize Docker (falls back to subprocess if unavailable)

**Internal flow:**
```
MCPApi.__init__()
├── Create directories
├── MCPConnector() - registers MCP servers
├── MCPRuntime() - routes mcp_call() to servers
├── CodeExecutor() - executes code in sandbox
│   └── _init_docker() - attempts Docker initialization
├── SkillManager() - manages skill persistence
└── CheckpointManager() - manages task checkpoints
```

#### 2. Register MCP Server

```python
api.add_mcp_server(
    name="filesystem",
    command="npx -y @modelcontextprotocol/server-filesystem /tmp"
)
```

**What happens:**
- Stores server config: name="filesystem", command to spawn it
- Parses command into parts: `["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]`
- Server **not started yet** - just registered

**The filesystem MCP server:**
- Official MCP server from Model Context Protocol
- Provides tools to read/write/list files
- Scoped to `/tmp` directory (can only access files there)

**Why `/tmp`?** This is a security boundary - the server can only access files within this directory.

#### 3. Generate Python APIs

```python
api.generate_apis()
```

**What happens:**

**Step 1: Connect to MCP Server**
```python
# Spawns process:
subprocess.Popen(["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"])

# Opens stdio communication
stdin, stdout = process.stdin, process.stdout
```

**Step 2: Introspect Tools**
```python
# Sends MCP protocol request:
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}

# Receives response:
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read contents of a file",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "File path"}
        },
        "required": ["path"]
      }
    },
    {
      "name": "write_file",
      "description": "Write contents to a file",
      ...
    },
    ...
  ]
}
```

**Step 3: Generate API Files**

For each tool, creates:

**`servers/filesystem/read_file/main.py`:**
```python
from mcp_skill_framework.runtime import mcp_call

def execute(path: str) -> Any:
    """Read contents of a file"""
    params = {}
    if path is not None:
        params['path'] = path

    return mcp_call(
        server="filesystem",
        tool="read_file",
        params=params
    )
```

**`servers/filesystem/read_file/README.md`:**
```markdown
# read_file

**Domain:** filesystem
**Category:** API

## Description

Read contents of a file

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | str | Yes | File path |

## Returns

`Any` - Tool execution result

## Example Usage

```python
from servers.filesystem.read_file import execute

result = execute(path="/tmp/test.txt")
print(result)
```
```

**`servers/filesystem/read_file/__init__.py`:**
```python
"""Read contents of a file"""

from .main import execute

__all__ = ['execute']
```

**Complete directory structure after generation:**
```
servers/
└── filesystem/
    ├── read_file/
    │   ├── main.py
    │   ├── README.md
    │   └── __init__.py
    ├── write_file/
    │   ├── main.py
    │   ├── README.md
    │   └── __init__.py
    ├── list_directory/
    │   ├── main.py
    │   ├── README.md
    │   └── __init__.py
    └── ... (other tools)
```

**Key insight:** These are **thin wrappers** that call `mcp_call()`. The actual MCP communication happens in the runtime.

#### 4. Start Runtime

```python
api.start()
```

**What happens:**

**Step 1: Reconnect to MCP Servers**
```python
# For each registered server:
connector.connect_all()
├── Spawn MCP server process
├── Open stdio streams
├── Send initialize request
└── Store ClientSession in connections dict
```

**Step 2: Register Connections in Runtime**
```python
runtime.register_servers(connections)
# Now runtime can route mcp_call() to actual servers
```

**Step 3: Set Started Flag**
```python
self._started = True
# API is now ready for code execution
```

#### 5. Example 1: Execute Simple Code

```python
code1 = """
from servers.filesystem.read_file import execute as read_file

try:
    content = read_file("/tmp/test.txt")
    print(f"File content: {content}")
except Exception as e:
    print(f"Error: {e}")
"""

result1 = api.execute(code1)
```

**Detailed Execution Flow:**

**Step 1: Code Wrapping**

```python
# Original agent code
code = """
from servers.filesystem.read_file import execute as read_file
content = read_file("/tmp/test.txt")
print(content)
"""

# Wrapper adds environment setup
wrapper = """
import sys
import os

# Add to Python path (Docker paths)
sys.path.insert(0, '/workspace/src')
sys.path.insert(0, '/workspace/servers')
sys.path.insert(0, '/workspace/skills')

# Change working directory
os.chdir('/workspace')

# Import runtime
from mcp_skill_framework.runtime import _runtime_instance

# Verify runtime available
if _runtime_instance is None:
    print("ERROR: MCP Runtime not initialized", file=sys.stderr)
    sys.exit(1)

# Execute user code (indented)
try:
    from servers.filesystem.read_file import execute as read_file
    content = read_file("/tmp/test.txt")
    print(content)
except Exception as e:
    import traceback
    print("ERROR:", str(e), file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
"""
```

**Step 2: Write to Temp File**
```python
# Creates: /tmp/tmpXXXXX.py
temp_file.write(wrapper_code)
```

**Step 3: Docker Execution (if available)**

```bash
docker run \
  --rm \
  --network host \
  --memory 512m \
  --cpu-period 100000 \
  --cpu-quota 50000 \
  -v /host/project/src:/workspace/src:ro \
  -v /host/project/servers:/workspace/servers:ro \
  -v /host/project/skills:/workspace/skills:rw \
  -v /host/project/tasks:/workspace/tasks:rw \
  -v /host/project/tmp:/workspace/tmp:rw \
  -e PYTHONPATH=/workspace/src:/workspace \
  -w /workspace \
  mcp-skill-framework-executor:latest \
  python /workspace/tmp/tmpXXXXX.py
```

**What the volumes do:**
- `/workspace/src` (ro): Framework source code - needed for imports
- `/workspace/servers` (ro): Generated APIs - agent imports from here
- `/workspace/skills` (rw): Skills directory - agent can save new skills
- `/workspace/tasks` (rw): Checkpoints - agent can create checkpoints
- `/workspace/tmp` (rw): Temporary files - execution scripts

**Why `network_mode='host'`?**
The MCP server runs on the host using stdio. The container needs to communicate with it, which requires host network access.

**Step 4: Inside Container Execution**

```python
# Python interpreter starts
# Wrapper code executes:

# 1. Set up paths
sys.path = ['/workspace/src', '/workspace/servers', '/workspace/skills', ...]

# 2. Import runtime (from mounted src/)
from mcp_skill_framework.runtime import _runtime_instance
# This imports the HOST's runtime.py via volume mount
# _runtime_instance is the global variable set when runtime initialized

# 3. Execute agent code
from servers.filesystem.read_file import execute as read_file
# This imports from /workspace/servers/filesystem/read_file/__init__.py
# Which imports from main.py
# Which defines execute() function
```

**Step 5: mcp_call() Execution**

```python
# Agent calls:
content = read_file("/tmp/test.txt")

# Which calls (in servers/filesystem/read_file/main.py):
def execute(path: str) -> Any:
    return mcp_call(
        server="filesystem",
        tool="read_file",
        params={"path": path}
    )

# mcp_call() is defined in runtime.py:
def mcp_call(server: str, tool: str, params: dict):
    return _runtime_instance.call(server, tool, params)

# _runtime_instance.call() does:
class MCPRuntime:
    def call(self, server, tool, params):
        session = self.servers["filesystem"]  # ClientSession on host
        result = asyncio.run(
            session.call_tool(tool, params)
        )
        return result
```

**Communication flow:**
```
Container                                Host
   │                                      │
   │  read_file("/tmp/test.txt")         │
   │  ──────────────────────────>        │
   │                                      │
   │  mcp_call("filesystem",              │
   │           "read_file",                │
   │           {"path": "..."})           │
   │  ──────────────────────────>        │
   │                                      │
   │                                      │  MCP Server
   │                                      │  (stdio process)
   │                                      │  ──────────>
   │                                      │  read file
   │                                      │  <──────────
   │                                      │  content
   │  <──────────────────────────         │
   │  "Hello, World!"                     │
   │                                      │
   │  print("File content: ...")          │
   │  stdout: "File content: Hello..."    │
```

**Step 6: Result Capture**

```python
# Container prints to stdout
stdout: "File content: Hello, World!"

# Docker captures stdout
container.logs() = b"File content: Hello, World!\n"

# Decode and return
return {
    'success': True,
    'result': "File content: Hello, World!\n",
    'stdout': "File content: Hello, World!\n",
    'stderr': '',
}
```

**Step 7: Cleanup**
```python
# Container removed automatically (--rm flag)
# Temp file deleted
Path(temp_file).unlink()
```

#### 6. Example 2: Save as Skill

```python
code2 = """
'''Count lines in a file.'''

from servers.filesystem.read_file import execute as read_file

def count_lines(filepath):
    content = read_file(filepath)
    return len(content.split('\\n'))

lines = count_lines("/tmp/test.txt")
print(f"File has {lines} lines")
"""

result2 = api.execute(
    code2,
    save_as_skill="count_lines",
    category="file_operations"
)
```

**What happens:**

**Execution Phase:** Same as Example 1 (wraps, runs in Docker/subprocess)

**Skill Saving Phase:**

```python
# In framework.py execute() method:
if save_as_skill:
    skill_manager.save_skill(
        code=code2,
        name="count_lines",
        category="file_operations"
    )
```

**SkillManager.save_skill() does:**

**Step 1: Create Directory**
```python
skill_dir = skills_dir / "file_operations" / "count_lines"
skill_dir.mkdir(parents=True, exist_ok=True)
```

**Step 2: Save Code**
```python
# skills/file_operations/count_lines/main.py
main_py_path.write_text(code2)
```

**Step 3: Extract Docstring**
```python
import ast
tree = ast.parse(code2)
docstring = ast.get_docstring(tree)  # "Count lines in a file."
```

**Step 4: Generate README**
```python
readme_content = f"""# count_lines

**Category:** file_operations
**Created:** 2025-11-16

## Description

Count lines in a file.

## Usage

```python
from skills.file_operations.count_lines import *

# Use the skill here
```

## Tags

file_operations, count_lines
"""

readme_path.write_text(readme_content)
```

**Step 5: Generate Metadata**
```python
metadata = {
    "name": "count_lines",
    "category": "file_operations",
    "created": "2025-11-16T10:30:00",
    "usage_count": 0,
    "tags": []
}

meta_path.write_text(json.dumps(metadata, indent=2))
```

**Step 6: Create __init__.py**
```python
init_content = """\"\"\"Count lines in a file.\"\"\"

from .main import *

__all__ = ['count_lines']
"""

init_path.write_text(init_content)
```

**Final Structure:**
```
skills/
└── file_operations/
    └── count_lines/
        ├── main.py          # The agent's code
        ├── README.md        # Auto-generated docs
        ├── __init__.py      # Makes it importable
        └── .meta.json       # Metadata
```

**Future Reuse:**

```python
# In a later task, agent can:
from skills.file_operations.count_lines import count_lines

lines = count_lines("/tmp/data.txt")
# No need to regenerate this code!
```

**Why this matters:** The agent just composed a reusable pattern. Next time it needs to count lines, it doesn't need to write this code again - it can import the skill.

#### 7. Example 3: List Skills

```python
skills = api.list_skills()
print(f"Available skills: {len(skills)}")
for skill in skills:
    print(f"  - {skill['category']}/{skill['name']}")
```

**What happens:**

```python
# SkillManager.list_skills() does:

skills = []

# Scan all category directories
for category_dir in skills_dir.iterdir():
    # file_operations/, data_processing/, etc.

    for skill_dir in category_dir.iterdir():
        # count_lines/, process_batch/, etc.

        meta_path = skill_dir / ".meta.json"
        if meta_path.exists():
            metadata = json.loads(meta_path.read_text())
            metadata['path'] = f"{category_dir.name}/{skill_dir.name}"
            skills.append(metadata)

return skills
```

**Output:**
```
Available skills: 1
  - file_operations/count_lines
```

---

## Example 2: Checkpoint Demo

**File:** `examples/checkpoint_demo.py`

This demonstrates checkpointing for long-running tasks.

### Step-by-Step Breakdown

#### 1-3. Same Setup (Initialize, register, generate, start)

#### 4. Create a Checkpoint

```python
task_state = {
    "processed_files": ["file1.txt", "file2.txt"],
    "current_index": 2,
    "total_files": 10,
    "results": [
        {"name": "file1.txt", "size": 100},
        {"name": "file2.txt", "size": 200}
    ],
}

resume_code = """
from servers.filesystem.list_directory import execute as list_dir

remaining_files = ["file3.txt", "file4.txt", "file5.txt"]

for filename in remaining_files:
    print(f"Processing {filename}...")
    processed_files.append(filename)
    current_index += 1

print(f"Processed {current_index}/{total_files} files")
return {"status": "completed", "processed": current_index}
"""

api.create_checkpoint(
    task_id="file_processing_20251116",
    state=task_state,
    code=resume_code,
    description="Process all files in directory with progress tracking"
)
```

**What happens:**

**Step 1: Create Directory Structure**
```python
task_dir = tasks_dir / "file_processing_20251116"
task_dir.mkdir(parents=True, exist_ok=True)

data_dir = task_dir / "data"
data_dir.mkdir(exist_ok=True)
```

**Step 2: Serialize State as Python Code**

```python
# CheckpointManager._serialize_state_as_code() does:
import pprint

state_code_lines = []
for key, value in task_state.items():
    value_repr = pprint.pformat(value, width=80)
    state_code_lines.append(f"{key} = {value_repr}")

state_code = "\n".join(state_code_lines)
```

**Resulting state code:**
```python
processed_files = ['file1.txt', 'file2.txt']
current_index = 2
total_files = 10
results = [{'name': 'file1.txt', 'size': 100},
           {'name': 'file2.txt', 'size': 200}]
```

**Step 3: Generate checkpoint.py**

**`tasks/file_processing_20251116/checkpoint.py`:**
```python
"""
Checkpoint for task: file_processing_20251116
Description: Process all files in directory with progress tracking
Created: 2025-11-16T10:30:00
"""

# Task state
processed_files = ['file1.txt', 'file2.txt']
current_index = 2
total_files = 10
results = [{'name': 'file1.txt', 'size': 100},
           {'name': 'file2.txt', 'size': 200}]

# Resume function
def resume():
    """Resume task execution from this checkpoint."""
    from servers.filesystem.list_directory import execute as list_dir

    remaining_files = ["file3.txt", "file4.txt", "file5.txt"]

    for filename in remaining_files:
        print(f"Processing {filename}...")
        processed_files.append(filename)
        current_index += 1

    print(f"Processed {current_index}/{total_files} files")
    return {"status": "completed", "processed": current_index}

if __name__ == "__main__":
    result = resume()
    print(f"Resume completed: {result}")
```

**Why this is brilliant:**
- State variables are **in scope** when resume() executes
- Variables are mutable - `processed_files.append()` works
- Human-readable - you can edit this file if needed
- Git-friendly - can track progress in version control
- Portable - copy this file = copy state

**Step 4: Generate README**

**`tasks/file_processing_20251116/README.md`:**
```markdown
# Task: file_processing_20251116

**Status:** Active
**Created:** 2025-11-16 10:30:00

## Description

Process all files in directory with progress tracking

## State

See `checkpoint.py` for full state details.

## Resume

To resume this task:

```python
from tasks.file_processing_20251116.checkpoint import resume

result = resume()
```
```

**Step 5: Generate Metadata**

**`tasks/file_processing_20251116/.meta.json`:**
```json
{
  "task_id": "file_processing_20251116",
  "description": "Process all files in directory with progress tracking",
  "created": "2025-11-16T10:30:00",
  "status": "active"
}
```

#### 5. Resume from Checkpoint

```python
result = api.resume_checkpoint("file_processing_20251116")
```

**What happens:**

**Step 1: Locate Checkpoint**
```python
checkpoint_path = tasks_dir / "file_processing_20251116" / "checkpoint.py"
```

**Step 2: Load as Python Module**
```python
import importlib.util

spec = importlib.util.spec_from_file_location(
    "checkpoint",
    checkpoint_path
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

**What happens when module loads:**
```python
# Python executes the checkpoint.py file:

# 1. Module docstring (skipped)

# 2. State variables defined
processed_files = ['file1.txt', 'file2.txt']  # In module scope
current_index = 2
total_files = 10
results = [...]

# 3. resume() function defined
def resume():
    # Function has access to module-level variables
    # via closure / scope
    ...

# 4. if __name__ == "__main__": (skipped, not main)
```

**Step 3: Execute resume()**
```python
result = module.resume()
```

**Execution flow inside resume():**
```python
def resume():
    # State variables are in scope (module-level)
    # processed_files = ['file1.txt', 'file2.txt']
    # current_index = 2
    # total_files = 10

    from servers.filesystem.list_directory import execute as list_dir

    remaining_files = ["file3.txt", "file4.txt", "file5.txt"]

    for filename in remaining_files:
        print(f"Processing {filename}...")
        # Output: Processing file3.txt...
        #         Processing file4.txt...
        #         Processing file5.txt...

        processed_files.append(filename)
        # processed_files is now:
        # ['file1.txt', 'file2.txt', 'file3.txt', 'file4.txt', 'file5.txt']

        current_index += 1
        # current_index is now: 3, then 4, then 5

    print(f"Processed {current_index}/{total_files} files")
    # Output: Processed 5/10 files

    return {"status": "completed", "processed": current_index}
    # Returns: {"status": "completed", "processed": 5}
```

**Step 4: Return Result**
```python
# api.resume_checkpoint() returns:
{"status": "completed", "processed": 5}
```

**Why this works:**
- Python module loading executes the file
- State variables become module-level variables
- `resume()` function has access to those variables via scope
- Variables are mutable (lists, dicts can be modified)
- It's just Python - no special serialization needed

---

## Real-World Usage Patterns

### Pattern 1: Skill Accumulation Over Time

**Day 1: Direct API Usage**
```python
code = """
from servers.database.query import execute as query

results = query("SELECT * FROM users WHERE active = true")
for user in results:
    print(user)
"""

api.execute(code)
```

**Day 2: Discover Pattern, Save as Skill**
```python
code = """
'''Get all active users from database.'''

from servers.database.query import execute as query

def get_active_users():
    return query("SELECT * FROM users WHERE active = true")

users = get_active_users()
print(f"Found {len(users)} active users")
"""

api.execute(code, save_as_skill="get_active_users", category="database")
```

**Day 3: Reuse Skill**
```python
code = """
from skills.database.get_active_users import get_active_users

users = get_active_users()
# Process users...
"""

api.execute(code)
```

**Day 5: Compose Skills**
```python
code = """
from skills.database.get_active_users import get_active_users
from skills.email.send_batch import send_batch
from skills.reporting.generate_report import generate_report

# Get data
users = get_active_users()

# Generate report
report = generate_report(users)

# Send emails
send_batch(users, report)
"""

api.execute(code, save_as_skill="weekly_user_report", category="workflows")
```

The agent **grows more capable** by accumulating reusable patterns!

### Pattern 2: Long-Running Task with Checkpoints

**Processing Large Dataset:**

```python
code = """
from servers.database.query import execute as query
from servers.api.post import execute as post_api

# Fetch all records (could be millions)
records = query("SELECT * FROM large_table")

processed = 0
total = len(records)

for i, record in enumerate(records):
    # Process each record
    result = post_api(f"/process/{record['id']}", data=record)
    processed += 1

    # Checkpoint every 1000 records
    if processed % 1000 == 0:
        print(f"Progress: {processed}/{total}")
        # Save checkpoint here
"""

# If this crashes at record 5432, you lose all progress!
```

**Better: With Checkpointing:**

```python
# Initial run
code = """
from servers.database.query import execute as query

records = query("SELECT * FROM large_table")
total = len(records)

print(f"Starting processing of {total} records")
"""

api.execute(code)

# Create checkpoint after every 1000 records
for batch_start in range(0, total, 1000):
    batch_end = min(batch_start + 1000, total)

    state = {
        "batch_start": batch_start,
        "batch_end": batch_end,
        "total": total,
        "processed_count": batch_start
    }

    resume_code = f"""
from servers.database.query import execute as query
from servers.api.post import execute as post_api

records = query("SELECT * FROM large_table LIMIT 1000 OFFSET {{batch_start}}")

for record in records:
    result = post_api(f"/process/{{record['id']}}", data=record)
    processed_count += 1

print(f"Batch complete: {{processed_count}}/{{total}}")
"""

    api.create_checkpoint(
        task_id=f"batch_{batch_start}",
        state=state,
        code=resume_code,
        description=f"Processing records {batch_start}-{batch_end}"
    )

    # Execute this batch
    api.resume_checkpoint(f"batch_{batch_start}")
```

**Now if it crashes at record 5432:**
- You have checkpoints at 0, 1000, 2000, 3000, 4000, 5000
- Resume from checkpoint `batch_5000`
- Only lose 432 records worth of work, not 5432!

### Pattern 3: Progressive Skill Refinement

**Version 1: Basic Implementation**
```python
code = """
def process_data(data):
    # Basic processing
    return [x * 2 for x in data]
"""

api.execute(code, save_as_skill="process_data", category="data")
```

**Version 2: Add Error Handling**
```python
code = """
def process_data(data):
    results = []
    for x in data:
        try:
            results.append(x * 2)
        except Exception as e:
            print(f"Error processing {x}: {e}")
            results.append(None)
    return results
"""

# Overwrites previous version
api.execute(code, save_as_skill="process_data", category="data")
```

**Version 3: Add Logging and Optimization**
```python
code = """
import logging

def process_data(data):
    logger = logging.getLogger(__name__)
    logger.info(f"Processing {len(data)} items")

    # Optimized with list comprehension
    results = []
    for x in data:
        try:
            results.append(x * 2)
        except Exception as e:
            logger.error(f"Error processing {x}: {e}")
            results.append(None)

    logger.info(f"Completed: {len(results)} results")
    return results
"""

api.execute(code, save_as_skill="process_data", category="data")
```

Skills **evolve and improve** over time!

---

## Key Takeaways

### Example 1 (Basic Usage) Demonstrates:
1. **Zero-config MCP usage** - Just provide server command
2. **Automatic API generation** - MCP tools → Python functions
3. **Progressive disclosure** - Agents explore APIs via filesystem
4. **Skill accumulation** - Code becomes reusable assets
5. **Token efficiency** - Agents write code, not verbose tool calls

### Example 2 (Checkpoint Demo) Demonstrates:
1. **State as code** - Not JSON/pickle, actual Python
2. **Human-readable checkpoints** - Can inspect/modify manually
3. **Resumable execution** - Pick up exactly where you left off
4. **Git-friendly** - Version control your agent's progress
5. **Composable patterns** - Checkpoints can import skills

### The Big Picture:

**Traditional Approach:**
```
Agent → [sees tool schemas] → Calls tools → Uses tokens → Forgets patterns
```

**Our Approach:**
```
Agent → [writes code] → Code becomes skill → Agent reuses skill → Gets smarter
                                ↓
                         Checkpoints progress → Can resume
```

The agent **compounds its knowledge** over time, getting more capable with each task!

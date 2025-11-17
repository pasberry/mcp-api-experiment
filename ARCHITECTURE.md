# MCP Skill Framework Architecture

## Overview

The MCP Skill Framework is infrastructure for building agents that grow smarter over time by accumulating reusable skills. It sits between MCP servers and agent frameworks, converting MCP tools into clean Python APIs.

## Core Concept

**Traditional Approach:**
```
Agent → [sees all MCP tool schemas] → Calls MCP tools → High token usage
```

**Our Approach:**
```
MCP Servers → Framework (generates Python APIs) → Agent → [writes code] → Skills accumulate
```

## Architecture Layers

### Layer 1: MCP Connection (`connector.py`)

**Purpose:** Connect to MCP servers and introspect their capabilities

**Components:**
- `MCPConnector`: Manages MCP server connections via stdio
- `ToolSchema`: Represents MCP tool definitions

**Flow:**
1. User registers MCP server with command (e.g., `npx @model/server`)
2. Connector spawns server process
3. Introspects available tools via `list_tools()`
4. Parses tool schemas (parameters, descriptions)

### Layer 2: API Generation (`connector.py` + `templates.py`)

**Purpose:** Generate semantic directory structure with Python APIs

**Output Structure:**
```
servers/
└── {server_name}/
    └── {tool_name}/
        ├── main.py        # Python wrapper function
        ├── README.md      # Tool documentation
        └── __init__.py    # Module imports
```

**Generated `main.py` Example:**
```python
from mcp_skill_framework.runtime import mcp_call

def execute(param1: str, param2: int = 0) -> Any:
    """Tool description here."""
    params = {}
    if param1 is not None:
        params['param1'] = param1
    if param2 is not None:
        params['param2'] = param2

    return mcp_call(
        server="server_name",
        tool="tool_name",
        params=params
    )
```

**Key Design:**
- Each tool gets its own directory (semantic paths)
- README.md enables progressive disclosure
- APIs hide MCP protocol details

### Layer 3: Runtime Execution (`runtime.py`)

**Purpose:** Route Python function calls to MCP servers

**Components:**
- `MCPRuntime`: Maintains MCP connections, routes calls
- `mcp_call()`: Global function used by generated APIs

**Flow:**
1. Generated API calls `mcp_call(server, tool, params)`
2. Runtime looks up server connection
3. Executes MCP tool call via async protocol
4. Returns result to caller

**Key Design:**
- Single global runtime instance
- Async MCP calls wrapped in sync interface
- Error handling and logging

### Layer 4: Code Execution (`executor.py`)

**Purpose:** Execute agent code in isolated environment

**Current Implementation:** Subprocess isolation
**Future:** Docker containerization

**Flow:**
1. Agent writes code using generated APIs
2. Executor creates wrapper script
3. Executes in subprocess with proper PYTHONPATH
4. Captures stdout/stderr
5. Returns result

**Environment Setup:**
```
PYTHONPATH includes:
- src/ (framework code)
- servers/ (generated APIs)
- skills/ (accumulated skills)
```

### Layer 5: Skill Management (`skill_manager.py`)

**Purpose:** Persist agent solutions as reusable skills

**Output Structure:**
```
skills/
└── {category}/
    └── {skill_name}/
        ├── main.py        # Agent's code
        ├── README.md      # Auto-generated docs
        ├── __init__.py    # Module imports
        └── .meta.json     # Metadata & usage tracking
```

**Features:**
- Extract docstrings from code
- Generate README automatically
- Track usage statistics
- Skill discovery by category/tags

**Growth Pattern:**
- Week 1: Agent uses `servers/` APIs directly
- Week 2: Agent creates reusable patterns → `skills/`
- Week 3: Agent reuses `skills/` for complex tasks
- Agent capability compounds over time

### Layer 6: Checkpoint Management (`checkpoint_manager.py`)

**Purpose:** Save and resume task state as code

**Output Structure:**
```
tasks/
└── {task_id}/
    ├── checkpoint.py      # Resumable state as code
    ├── README.md          # Progress description
    ├── .meta.json         # Metadata
    └── data/              # Artifacts
```

**Checkpoint Code Example:**
```python
# Task state
processed_items = ['item1', 'item2']
current_index = 2
total_count = 100

# Resume function
def resume():
    # Continue from where we left off
    for i in range(current_index, total_count):
        process_item(i)
        current_index = i

    return {"status": "completed"}
```

**Key Design:**
- State serialized as Python variables
- Human-readable and git-friendly
- Resume logic is explicit code
- Portable across environments

### Layer 7: Framework Orchestration (`framework.py`)

**Purpose:** Unified API that ties all components together

**Public Interface:**
```python
api = MCPApi()
api.add_mcp_server(name, command)
api.generate_apis()
api.start()
api.execute(code, save_as_skill="name")
api.save_skill(code, name, category)
api.list_skills()
api.create_checkpoint(task_id, state, code)
api.resume_checkpoint(task_id)
api.stop()
```

**Lifecycle:**
1. **Setup:** Register MCP servers
2. **Generate:** Create Python APIs
3. **Runtime:** Start MCP connections
4. **Execute:** Run agent code
5. **Persist:** Save skills and checkpoints
6. **Shutdown:** Cleanup connections

## Data Flow

### API Generation Flow

```
MCP Server
    ↓ (stdio connection)
MCPConnector.introspect_server()
    ↓ (tool schemas)
templates.generate_main_py()
templates.generate_readme_md()
    ↓
servers/{server}/{tool}/main.py
servers/{server}/{tool}/README.md
```

### Execution Flow

```
Agent writes code
    ↓
MCPApi.execute(code)
    ↓
CodeExecutor.execute()
    ↓ (subprocess)
User code runs
    ↓ (imports from servers/)
Generated API called
    ↓
mcp_call(server, tool, params)
    ↓
MCPRuntime.call()
    ↓ (async MCP protocol)
MCP Server processes request
    ↓
Result returned to agent
```

### Skill Accumulation Flow

```
Agent solves problem
    ↓
MCPApi.execute(code, save_as_skill=True)
    ↓
SkillManager.save_skill()
    ↓
skills/{category}/{name}/main.py
    ↓ (next task)
Agent imports from skills/
    ↓
Skill reused and enhanced
```

## Design Decisions

### 1. Semantic Directory Paths

**Decision:** Each tool/skill gets its own directory

**Rationale:**
- Enables README.md for progressive disclosure
- Clean namespace (no name collisions)
- Room for additional files (tests, examples)

### 2. README.md for Discovery

**Decision:** Every API and skill has a README

**Rationale:**
- Agents can read descriptions before importing
- Reduces tokens (agent only loads what it needs)
- Human-readable documentation

### 3. Code-Based Checkpoints

**Decision:** Serialize state as Python code, not JSON/pickle

**Rationale:**
- Human-readable (developers can inspect)
- Git-friendly (diffs, versioning)
- Portable (no pickle compatibility issues)
- Debuggable (modify and re-run)

### 4. Subprocess (not Docker) for MVP

**Decision:** Use subprocess isolation initially

**Rationale:**
- Simpler to implement and test
- No Docker dependency for POC
- Can upgrade to Docker later
- Sufficient isolation for trusted code

### 5. Sync API over Async

**Decision:** Public API is synchronous

**Rationale:**
- Easier for agent frameworks to use
- MCP async complexity hidden internally
- Event loop managed by framework

## Future Enhancements

### Docker Sandboxing

Replace subprocess with full Docker containers:
- Better isolation
- Resource limits (CPU, memory)
- Network sandboxing
- Easy cleanup

### API Versioning

Support multiple versions of generated APIs:
```
servers/{server}/{tool}/v1/main.py
servers/{server}/{tool}/v2/main.py
```

### Skill Validation

Add optional validation before saving skills:
- Syntax checking
- Security scanning
- Unit test generation

### Multi-Agent Skills Registry

Enable skills to be shared across agents:
- Central skills repository
- Skill ratings/reviews
- Dependency management

### Incremental API Generation

Generate APIs on-demand instead of upfront:
- First time a tool is called → generate API
- Reduces initial overhead
- True progressive disclosure

## Token Efficiency Analysis

**Traditional MCP Approach:**
```
Context includes all tool schemas: ~10,000 tokens
Agent calls 3 tools: ~12,000 tokens total
```

**Our Approach:**
```
Agent sees directory structure: ~100 tokens
Agent reads 3 READMEs: ~500 tokens
Agent writes code: ~300 tokens
Total: ~900 tokens (91% reduction)
```

## Conclusion

The MCP Skill Framework provides infrastructure for building agents that:
- ✅ Use MCP servers efficiently (massive token reduction)
- ✅ Grow smarter over time (skill accumulation)
- ✅ Handle long-running tasks (checkpointing)
- ✅ Work with any agent framework (framework-agnostic)

It's not an agent itself—it's the foundation that agent builders use to create more capable, efficient agents.

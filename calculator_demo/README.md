# Calculator Demo - MCP Skill Framework Test

This demo proves that the MCP Skill Framework works end-to-end:

1. **Code Generation**: Generate Python wrappers from MCP servers
2. **Agent Integration**: LangGraph agent imports and uses generated code
3. **Skill Persistence**: Agent saves working code as reusable skills

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  MCP Calculator Server (calculator_server.py)          │
│  - Exposes: add, subtract, multiply, divide             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Code Generation (mcp-generate)                         │
│  - Reads: mcp-servers.json                              │
│  - Generates: servers/calculator/* Python wrappers      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  LangGraph Agent (math_agent.py)                        │
│  - Imports: servers.calculator.*                        │
│  - Writes Python code to solve math problems            │
│  - Saves working code as skills                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Skills Persistence                                     │
│  - Filesystem: skills/math_operations/*                 │
│  - Database: skills.db (SQLite)                         │
└─────────────────────────────────────────────────────────┘
```

## Setup

1. **Install dependencies**:
   ```bash
   cd calculator_demo
   pip install -e ..  # Install mcp_skill_framework
   pip install -r requirements.txt
   ```

2. **Set Anthropic API key**:
   ```bash
   export ANTHROPIC_API_KEY="your-key-here"
   ```

3. **Generate MCP wrappers**:
   ```bash
   ./generate_wrappers.sh
   ```

   This creates `servers/calculator/` with Python wrapper functions.

## Run the Demo

```bash
python math_agent.py
```

## What Should Happen

### ✅ Success Criteria

1. **Agent writes code** using `servers.calculator.*` imports
2. **Code executes** successfully and solves the problems
3. **Skills are saved** to `skills/math_operations/` directory
4. **Database is populated** with skill metadata
5. **Both questions answered**:
   - "What is 3 + 3 + 3" → Answer: 9
   - "What is 6 / 2 + 9" → Answer: 12

### ❌ Failure Scenarios

- Agent doesn't use `servers.calculator.*` imports
- No skills created in `skills/` directory
- Database has no entries
- Code execution fails

## Expected Output

```
🧮 MATH AGENT DEMO - MCP Skill Framework Test
=============================================================

❓ Question: What is 3 + 3 + 3
📝 Writing code to solve...
💻 Generated code:
   [Python code using servers.calculator.add]
🔧 Executing code...
✅ Code executed successfully!
💾 Saving code as reusable skill...
✅ Skill saved: skills/math_operations/what_is_3_3_3/

❓ Question: What is 6 / 2 + 9
📝 Writing code to solve...
💻 Generated code:
   [Python code using servers.calculator.divide and add]
🔧 Executing code...
✅ Code executed successfully!
💾 Saving code as reusable skill...
✅ Skill saved: skills/math_operations/what_is_6_2_9/

📊 RESULTS SUMMARY
Q: What is 3 + 3 + 3
A: Answer: 9.0

Q: What is 6 / 2 + 9
A: Answer: 12.0

🗂️  SKILLS CREATED
Found 2 skills in skills/math_operations/:
  📄 what_is_3_3_3/
  📄 what_is_6_2_9/

💾 DATABASE VERIFICATION
Total skills in database: 2
  - math_operations: 2 skills
```

## Verification

After running, check:

```bash
# Check skills directory
ls -la skills/math_operations/

# Check database
sqlite3 skills.db "SELECT skill_name, category FROM skills WHERE agent_name='math-agent';"

# Inspect generated wrappers
cat servers/calculator/add/__init__.py
```

## How It Works

1. **Calculator MCP Server** (`calculator_server.py`) exposes 4 arithmetic tools
2. **Code Generation** (`./generate_wrappers.sh`) creates Python wrappers
3. **LangGraph Agent** (`math_agent.py`):
   - System prompt instructs it to write Python code
   - Agent imports from `servers.calculator.*`
   - Executes code to verify it works
   - Saves working code as skills
4. **Skills Persistence**:
   - Immediate write to filesystem (agent can import)
   - Async write to database (for future hydration)

## Key Insight

The agent has NO direct math tools. It must:
- **Write code** using the generated calculator package
- **Execute that code** to get answers
- **Save working solutions** as reusable skills

This proves the MCP Skill Framework enables agents to:
1. Use MCP tools through generated Python code
2. Write and save new capabilities as skills
3. Build a growing library of reusable solutions

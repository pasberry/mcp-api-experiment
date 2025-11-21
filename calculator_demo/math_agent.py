#!/usr/bin/env python3
"""
LangGraph Math Agent - Writes Python code to solve math problems

This agent:
1. Receives math questions
2. Writes Python code using the generated servers.calculator.* package
3. Executes the code to verify it works
4. Saves working solutions as reusable skills
5. Returns the answer

Success criteria:
- Agent MUST use servers.calculator.* imports in its code
- Agent MUST save working code as skills to skills/ directory
- Skills MUST be persisted to SQLite database
"""
import sys
import os
import inspect
import asyncio
from pathlib import Path
from typing import TypedDict, Annotated
import operator

# Add current directory to path so we can import generated servers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Import MCP Skill Framework
from src import MCPApi


# Agent State
class AgentState(TypedDict):
    """State for the math agent."""
    question: str
    code: str
    result: str
    error: str
    messages: Annotated[list, operator.add]
    attempts: int


# Initialize MCP Skill Framework
print("🚀 Initializing MCP Skill Framework...")
api = MCPApi(
    agent_name="math-agent",
    servers_dir="servers",
    skills_dir="skills",
    skills_db="skills.db",
    telemetry_db=None,  # Disable telemetry for demo
)

# Register calculator MCP server
calculator_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calculator_server.py")
api.add_mcp_server(
    name="calculator",
    command=f"python {calculator_script}",
)

print("📦 Starting MCP runtime (connecting to calculator server)...")
api.start()
print("✅ MCP runtime ready!\n")

# Initialize LLM
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    temperature=0,
)

# System prompt for code-writing agent
CODE_WRITER_PROMPT = """You are a math problem-solving agent that writes Python code to solve problems.

CRITICAL REQUIREMENTS:
1. You MUST write Python code that uses the generated calculator tools from the servers.calculator package
2. You MUST import the specific operations you need like this:
   - from servers.calculator.add import calculator_add
   - from servers.calculator.subtract import calculator_subtract
   - from servers.calculator.multiply import calculator_multiply
   - from servers.calculator.divide import calculator_divide

3. Each function call returns a JSON string with {{"result": <number>}}
4. You MUST parse the JSON response to get the actual number
5. Write clean, working Python code that solves the problem step by step

EXAMPLE:
Question: "What is 5 + 3?"

Your code:
```python
import json
from servers.calculator.add import calculator_add

# Add 5 + 3
result_json = calculator_add(a=5, b=3)
result_data = json.loads(result_json)
answer = result_data["result"]

print(f"Answer: {{answer}}")
```

ANOTHER EXAMPLE:
Question: "What is 10 / 2 + 3?"

Your code:
```python
import json
from servers.calculator.divide import calculator_divide
from servers.calculator.add import calculator_add

# First divide 10 / 2
divide_result_json = calculator_divide(a=10, b=2)
divide_data = json.loads(divide_result_json)
intermediate = divide_data["result"]

# Then add the result + 3
add_result_json = calculator_add(a=intermediate, b=3)
add_data = json.loads(add_result_json)
answer = add_data["result"]

print(f"Answer: {{answer}}")
```

Now write code to solve this problem: {question}

IMPORTANT: Only output valid Python code, nothing else. No markdown, no explanations."""


def code_writer_node(state: AgentState) -> dict:
    """Node that writes Python code to solve the math problem."""
    print(f"\n📝 Writing code to solve: {state['question']}")

    # Create prompt
    prompt = CODE_WRITER_PROMPT.format(question=state["question"])

    # Get code from LLM
    response = llm.invoke([{"role": "user", "content": prompt}])
    code = response.content.strip()

    # Clean up markdown code blocks if present
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()

    print(f"\n💻 Generated code:\n{code}\n")

    return {
        "code": code,
        "messages": [f"Generated code for: {state['question']}"],
        "attempts": state.get("attempts", 0) + 1,
    }


def code_executor_node(state: AgentState) -> dict:
    """Node that executes the Python code."""
    print("🔧 Executing code...")

    code = state["code"]

    # Create execution environment with access to servers package
    exec_globals = {
        "__name__": "__main__",
        "__builtins__": __builtins__,
    }

    # Capture print output
    from io import StringIO
    import sys

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        # Execute the code
        exec(code, exec_globals)

        # Get output
        output = captured_output.getvalue()
        sys.stdout = old_stdout

        print(f"✅ Code executed successfully!")
        print(f"📊 Output: {output.strip()}")

        return {
            "result": output.strip(),
            "error": "",
            "messages": [f"Code executed successfully: {output.strip()}"],
        }

    except Exception as e:
        sys.stdout = old_stdout
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")

        return {
            "result": "",
            "error": error_msg,
            "messages": [error_msg],
        }


def skill_saver_node(state: AgentState) -> dict:
    """Node that saves successful code as a skill."""
    print("\n💾 Saving code as reusable skill...")

    code = state["code"]
    question = state["question"]

    # Generate skill name from question
    skill_name = question.lower()
    skill_name = "".join(c if c.isalnum() or c == " " else "" for c in skill_name)
    skill_name = "_".join(skill_name.split()[:5])  # First 5 words

    # Create a proper function wrapper
    skill_code = f'''"""
Skill: {question}

This skill was automatically created by the math agent.
"""
import json
{code}
'''

    # Save skill
    api.save_skill(
        code=skill_code,
        name=skill_name,
        category="math_operations",
        tags=["math", "calculator", "auto-generated"],
        persist_to_db=True,
    )

    print(f"✅ Skill saved: skills/math_operations/{skill_name}/")
    print(f"📚 Skill persisted to database")

    return {
        "messages": [f"Saved skill: {skill_name}"],
    }


def should_retry(state: AgentState) -> str:
    """Decide if we should retry or continue."""
    if state.get("error") and state.get("attempts", 0) < 3:
        return "retry"
    elif state.get("error"):
        return "failed"
    else:
        return "success"


# Build the graph
def create_agent():
    """Create the LangGraph agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("write_code", code_writer_node)
    workflow.add_node("execute_code", code_executor_node)
    workflow.add_node("save_skill", skill_saver_node)

    # Add edges
    workflow.set_entry_point("write_code")
    workflow.add_edge("write_code", "execute_code")

    # Conditional edge after execution
    workflow.add_conditional_edges(
        "execute_code",
        should_retry,
        {
            "success": "save_skill",
            "retry": "write_code",
            "failed": END,
        }
    )

    workflow.add_edge("save_skill", END)

    # Compile
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


async def ask_agent(question: str) -> str:
    """Ask the agent a math question."""
    print(f"\n{'='*60}")
    print(f"❓ Question: {question}")
    print(f"{'='*60}")

    agent = create_agent()

    # Run agent
    initial_state = {
        "question": question,
        "code": "",
        "result": "",
        "error": "",
        "messages": [],
        "attempts": 0,
    }

    config = {"configurable": {"thread_id": "1"}}

    final_state = await agent.ainvoke(initial_state, config)

    if final_state.get("error"):
        return f"Failed to solve: {final_state['error']}"
    else:
        return final_state["result"]


async def main():
    """Run the demo."""
    print("\n" + "="*60)
    print("🧮 MATH AGENT DEMO - MCP Skill Framework Test")
    print("="*60)
    print("\nThis agent will:")
    print("1. Write Python code using servers.calculator.* tools")
    print("2. Execute the code to solve math problems")
    print("3. Save working solutions as reusable skills")
    print("\nLet's test it!\n")

    # Test questions
    questions = [
        "What is 3 + 3 + 3",
        "What is 6 / 2 + 9",
    ]

    results = []
    for question in questions:
        answer = await ask_agent(question)
        results.append((question, answer))
        print(f"\n✅ Final Answer: {answer}\n")

    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    for question, answer in results:
        print(f"Q: {question}")
        print(f"A: {answer}\n")

    # Check what skills were created
    print("\n" + "="*60)
    print("🗂️  SKILLS CREATED")
    print("="*60)

    skills_dir = Path("skills")
    if skills_dir.exists():
        math_ops = skills_dir / "math_operations"
        if math_ops.exists():
            skills = [d for d in math_ops.iterdir() if d.is_dir() and not d.name.startswith("__")]
            print(f"Found {len(skills)} skills in skills/math_operations/:\n")
            for skill in skills:
                print(f"  📄 {skill.name}/")
                main_file = skill / "__init__.py"
                if main_file.exists():
                    lines = main_file.read_text().split("\n")
                    print(f"      {len(lines)} lines of code")
        else:
            print("⚠️  No skills directory found!")

    # Check database
    print("\n" + "="*60)
    print("💾 DATABASE VERIFICATION")
    print("="*60)

    stats = await api.get_skill_stats()
    print(f"Total skills in database: {stats.get('total_skills', 0)}")
    if stats.get('by_category'):
        for category, count in stats['by_category'].items():
            print(f"  - {category}: {count} skills")

    print("\n" + "="*60)
    print("🎉 Demo complete!")
    print("="*60)

    # Cleanup
    api.stop()


if __name__ == "__main__":
    asyncio.run(main())

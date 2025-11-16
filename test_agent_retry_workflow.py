"""
Demonstrate the agent retry workflow with detailed error information.

This simulates how an agent would:
1. Write code that has an error
2. Receive detailed error information
3. Fix the code based on the error details
4. Successfully execute the corrected code
"""

import asyncio
from pathlib import Path
from mcp_skill_framework.executor import CodeExecutor
from mcp_skill_framework.runtime import MCPRuntime


def simulate_agent_workflow():
    """Simulate an agent iteratively fixing code based on error feedback."""

    # Setup executor
    base_dir = Path(__file__).parent
    servers_dir = base_dir / "servers"
    skills_dir = base_dir / "skills"
    tasks_dir = base_dir / "tasks"

    # Create directories
    servers_dir.mkdir(exist_ok=True)
    skills_dir.mkdir(exist_ok=True)
    tasks_dir.mkdir(exist_ok=True)

    # Initialize runtime and executor
    runtime = MCPRuntime()
    executor = CodeExecutor(
        servers_dir=servers_dir,
        skills_dir=skills_dir,
        tasks_dir=tasks_dir,
        runtime=runtime,
        use_docker=False
    )

    print("="*70)
    print("AGENT RETRY WORKFLOW DEMONSTRATION")
    print("="*70)
    print("\nScenario: Agent wants to count files in a directory\n")

    # Attempt 1: Agent makes a mistake with undefined variable
    print("\n" + "-"*70)
    print("ATTEMPT 1: Agent's first try (has a bug)")
    print("-"*70)

    code_attempt1 = """
# Count files in current directory
import os

files = os.listdir('.')
file_count = len(files)

# Oops! Agent made a typo - undefined variable
result = total_files  # Should be 'file_count'
"""

    print("Code:")
    print(code_attempt1)

    result1 = executor.execute(code_attempt1)

    print("\nExecution Result:")
    print(f"  Success: {result1['success']}")
    if not result1['success']:
        error = result1['error']
        print(f"  Error Type: {error['type']}")
        print(f"  Error Message: {error['message']}")
        print(f"  Line Number: {error['line_number']}")
        print(f"  Code Context: {error['code_context']}")
        print("\nAgent receives this error and analyzes it...")
        print(f"  -> NameError on line {error['line_number']}: {error['message']}")
        print(f"  -> The code tried to use 'total_files' but it doesn't exist")
        print(f"  -> Agent realizes it should use 'file_count' instead")

    # Attempt 2: Agent fixes the variable name but has logic error
    print("\n" + "-"*70)
    print("ATTEMPT 2: Agent fixes the NameError but makes a logic mistake")
    print("-"*70)

    code_attempt2 = """
# Count files in current directory
import os

files = os.listdir('.')
file_count = len(files)

# Fixed the variable name!
result = file_count

# But wait, agent wants to filter - only .py files
# This will cause an error because 'result' was already set
python_files = [f for f in files if f.endswith('.py')]
result = len(python_files) / 0  # Oops, division by zero
"""

    print("Code:")
    print(code_attempt2)

    result2 = executor.execute(code_attempt2)

    print("\nExecution Result:")
    print(f"  Success: {result2['success']}")
    if not result2['success']:
        error = result2['error']
        print(f"  Error Type: {error['type']}")
        print(f"  Error Message: {error['message']}")
        print(f"  Line Number: {error['line_number']}")
        print("\nAgent receives this error and analyzes it...")
        print(f"  -> ZeroDivisionError on line {error['line_number']}")
        print(f"  -> Agent realizes it shouldn't divide by zero")
        print(f"  -> Should just count the files, not divide")

    # Attempt 3: Agent gets it right!
    print("\n" + "-"*70)
    print("ATTEMPT 3: Agent finally gets it right!")
    print("-"*70)

    code_attempt3 = """
# Count files in current directory
import os

files = os.listdir('.')

# Count all files
total_files = len(files)

# Count Python files
python_files = [f for f in files if f.endswith('.py')]
python_file_count = len(python_files)

# Return structured data
result = {
    'total_files': total_files,
    'python_files': python_file_count,
    'other_files': total_files - python_file_count
}
"""

    print("Code:")
    print(code_attempt3)

    result3 = executor.execute(code_attempt3)

    print("\nExecution Result:")
    print(f"  Success: {result3['success']}")
    print(f"  Return Value: {result3['return_value']}")
    print(f"  Execution Time: {result3['execution_time_ms']:.2f}ms")

    print("\n" + "="*70)
    print("WORKFLOW COMPLETE!")
    print("="*70)
    print("\nKey Benefits of Structured Return:")
    print("  1. Agent receives ACTUAL DATA (file counts), not just stdout")
    print("  2. Errors include line numbers for precise debugging")
    print("  3. Error types help agent understand what went wrong")
    print("  4. Agent can iteratively improve code based on feedback")
    print("  5. Final result contains structured data for further processing")
    print("\nThis enables autonomous error recovery and code refinement!")
    print("="*70 + "\n")


if __name__ == "__main__":
    simulate_agent_workflow()

"""
Test the structured JSON return implementation for CodeExecutor.

This script tests:
1. Successful execution with return value
2. Execution with exception and error details
3. Execution with stdout and return value
4. Execution with syntax error
"""

import asyncio
import json
from pathlib import Path
from mcp_skill_framework.executor import CodeExecutor
from mcp_skill_framework.runtime import MCPRuntime


def print_result(test_name: str, result: dict) -> None:
    """Pretty print test result."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print('='*60)
    print(f"Success: {result['success']}")
    print(f"Return Value: {result.get('return_value')}")
    print(f"Stdout: {result.get('stdout', '')[:100]}")
    print(f"Stderr: {result.get('stderr', '')[:100]}")
    if result.get('error'):
        print(f"Error Type: {result['error']['type']}")
        print(f"Error Message: {result['error']['message']}")
        print(f"Line Number: {result['error'].get('line_number')}")
    print(f"Execution Time: {result.get('execution_time_ms', 0):.2f}ms")


async def main():
    # Setup executor
    base_dir = Path(__file__).parent
    servers_dir = base_dir / "servers"
    skills_dir = base_dir / "skills"
    tasks_dir = base_dir / "tasks"

    # Create directories
    servers_dir.mkdir(exist_ok=True)
    skills_dir.mkdir(exist_ok=True)
    tasks_dir.mkdir(exist_ok=True)

    # Initialize runtime (empty for these tests)
    runtime = MCPRuntime()

    # Create executor (use subprocess for testing)
    executor = CodeExecutor(
        servers_dir=servers_dir,
        skills_dir=skills_dir,
        tasks_dir=tasks_dir,
        runtime=runtime,
        use_docker=False  # Use subprocess for faster testing
    )

    # Test 1: Successful execution with return value
    code1 = """
# Calculate sum of numbers
numbers = [1, 2, 3, 4, 5]
result = sum(numbers)
"""
    result1 = executor.execute(code1)
    print_result("Successful execution with return value", result1)

    # Test 2: Execution with exception
    code2 = """
# This will raise a division by zero error
x = 10
y = 0
result = x / y
"""
    result2 = executor.execute(code2)
    print_result("Execution with exception", result2)

    # Test 3: Execution with stdout and return value
    code3 = """
# Print some output and return a value
print("Processing data...")
data = {"count": 42, "status": "complete"}
print(f"Found {data['count']} items")
result = data
"""
    result3 = executor.execute(code3)
    print_result("Execution with stdout and return value", result3)

    # Test 4: Execution with syntax error
    code4 = """
# This has a syntax error
def broken_function(
    x = 5
"""
    result4 = executor.execute(code4)
    print_result("Execution with syntax error", result4)

    # Test 5: Execution with explicit __result__
    code5 = """
# Set explicit result variable
data = []
for i in range(10):
    data.append(i * 2)

__result__ = {
    "data": data,
    "count": len(data),
    "max": max(data) if data else None
}
"""
    result5 = executor.execute(code5)
    print_result("Execution with explicit __result__", result5)

    # Test 6: Execution with NameError (accessing undefined variable)
    code6 = """
# Try to use undefined variable
result = undefined_variable + 10
"""
    result6 = executor.execute(code6)
    print_result("Execution with NameError", result6)

    print(f"\n{'='*60}")
    print("All tests completed!")
    print('='*60)


if __name__ == "__main__":
    asyncio.run(main())

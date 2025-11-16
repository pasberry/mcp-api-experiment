"""
Basic Usage Example

This example demonstrates:
1. Connecting to an MCP server
2. Generating Python APIs
3. Executing agent code
4. Saving skills
"""

import logging
from pathlib import Path
from mcp_skill_framework import Framework

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize framework
framework = Framework(
    servers_dir="servers",
    skills_dir="skills",
    tasks_dir="tasks"
)

# Register MCP server (filesystem server example)
# Install with: npx @modelcontextprotocol/server-filesystem
framework.add_mcp_server(
    name="filesystem",
    command="npx -y @modelcontextprotocol/server-filesystem /tmp"
)

# Generate Python APIs from MCP tools
print("Generating APIs...")
framework.generate_apis()

# Start the runtime
print("Starting framework...")
framework.start()

try:
    # Example 1: Execute simple code
    print("\n=== Example 1: Simple File Read ===")
    code1 = """
from servers.filesystem.read_file import execute as read_file

# Read a file
try:
    content = read_file("/tmp/test.txt")
    print(f"File content: {content}")
except Exception as e:
    print(f"Error: {e}")
"""

    result1 = framework.execute(code1)
    print(f"Result: {result1}")

    # Example 2: Execute code and save as skill
    print("\n=== Example 2: Save as Skill ===")
    code2 = """
'''Count lines in a file.'''

from servers.filesystem.read_file import execute as read_file

def count_lines(filepath):
    content = read_file(filepath)
    return len(content.split('\\n'))

# Example usage
lines = count_lines("/tmp/test.txt")
print(f"File has {lines} lines")
"""

    result2 = framework.execute(
        code2,
        save_as_skill="count_lines",
        category="file_operations"
    )
    print(f"Result: {result2}")

    # Example 3: List accumulated skills
    print("\n=== Example 3: List Skills ===")
    skills = framework.list_skills()
    print(f"Available skills: {len(skills)}")
    for skill in skills:
        print(f"  - {skill['category']}/{skill['name']}")

finally:
    # Cleanup
    print("\nStopping framework...")
    framework.stop()

print("\nDone!")

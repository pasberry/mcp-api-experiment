"""
Basic Usage Example

This example demonstrates the new MCP Skill Framework workflow:
1. Code generation: Converting MCP servers into Python libraries
2. Skill creation: Saving agent code as reusable skills
3. Skill persistence: Storing skills in database for future sessions
4. Skill hydration: Restoring skills from database on startup
"""

import asyncio
import logging
from pathlib import Path
from mcp_skill_framework import MCPApi

# Setup logging
logging.basicConfig(level=logging.INFO)


async def main():
    # Initialize API with agent name (required for database operations)
    api = MCPApi(
        agent_name="example-agent",
        servers_dir="servers",
        skills_dir="skills",
        skills_db="skills.db",
    )

    # ===================================================================
    # STEP 1: One-time code generation (developer workflow)
    # ===================================================================
    # Register MCP server (filesystem server example)
    # Install with: npx @modelcontextprotocol/server-filesystem
    print("\n=== Step 1: Code Generation ===")
    api.add_mcp_server(
        name="filesystem",
        command="npx -y @modelcontextprotocol/server-filesystem /tmp"
    )

    # Generate Python APIs from MCP tools
    print("Generating Python libraries from MCP servers...")
    api.generate_libraries()
    print("✓ Generated servers/filesystem/ package")
    print("  (Commit servers/ to git with your agent code)")

    # ===================================================================
    # STEP 2: Agent startup - Hydrate skills from database
    # ===================================================================
    print("\n=== Step 2: Hydration (Agent Startup) ===")
    count = await api.hydrate_skills()
    print(f"✓ Hydrated {count} skills from database")

    # Start the runtime to connect to MCP servers
    print("\n=== Step 3: Start Runtime ===")
    api.start()
    print("✓ Connected to MCP servers")

    try:
        # ===================================================================
        # STEP 4: Agent creates and saves new skills
        # ===================================================================
        print("\n=== Step 4: Create and Save Skills ===")

        # Example: Agent writes code that uses the generated API
        skill_code = '''
"""Count lines in a file."""

from servers.filesystem.read_file import filesystem_read_file

def count_lines(filepath):
    """
    Count the number of lines in a file.

    Args:
        filepath: Path to the file

    Returns:
        Number of lines in the file
    """
    content = filesystem_read_file(filepath)
    return len(content.split('\\n'))
'''

        # Save as skill (immediately written to filesystem + async persisted to DB)
        api.save_skill(
            code=skill_code,
            name="count_lines",
            category="file_operations",
            tags=["filesystem", "utility"]
        )
        print("✓ Saved skill: file_operations/count_lines")
        print("  - Immediately available in skills/file_operations/count_lines/")
        print("  - Persisted to database asynchronously")

        # Create another skill
        skill_code2 = '''
"""Get file size."""

from servers.filesystem.read_file import filesystem_read_file

def get_file_size(filepath):
    """
    Get the size of a file in bytes.

    Args:
        filepath: Path to the file

    Returns:
        File size in bytes
    """
    content = filesystem_read_file(filepath)
    return len(content)
'''

        api.save_skill(
            code=skill_code2,
            name="get_file_size",
            category="file_operations",
            tags=["filesystem", "utility"]
        )
        print("✓ Saved skill: file_operations/get_file_size")

        # ===================================================================
        # STEP 5: List and use accumulated skills
        # ===================================================================
        print("\n=== Step 5: List Skills ===")
        skills = api.list_skills()
        print(f"Available skills: {len(skills)}")
        for skill in skills:
            print(f"  - {skill['category']}/{skill['name']}")
            if 'tags' in skill:
                print(f"    Tags: {', '.join(skill['tags'])}")

        # Agent can now import and use skills:
        print("\n=== Step 6: Use Skills ===")
        print("Agent can now import skills:")
        print("  from skills.file_operations.count_lines import count_lines")
        print("  from skills.file_operations.get_file_size import get_file_size")

        # ===================================================================
        # STEP 7: Database statistics
        # ===================================================================
        print("\n=== Step 7: Database Stats ===")
        stats = await api.get_skill_stats()
        print(f"Agent: {stats['agent_name']}")
        print(f"Total skills: {stats['total_skills']}")
        print("Skills by category:")
        for category, count in stats['by_category'].items():
            print(f"  - {category}: {count}")

    finally:
        # Cleanup
        print("\n=== Cleanup ===")
        api.stop()
        print("✓ Disconnected from MCP servers")

    print("\n=== Next Session ===")
    print("On next agent startup:")
    print("  1. Call api.hydrate_skills() to restore all skills from database")
    print("  2. Skills will be written to skills/ directory")
    print("  3. Agent can immediately import and use them")
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

"""
Agent Discovery Pattern Example

This example shows how an agent framework (LangGraph, CrewAI, etc.)
would integrate the skill discovery tools for their agent.
"""

import asyncio
from typing import Optional
from mcp_skill_framework import MCPApi


# ===================================================================
# Discovery Tools for Agent
# ===================================================================
#
# NOTE: The agent doesn't need special tools for MCP servers.
# The servers/ package is just a regular Python package in the agent's
# environment that they can explore naturally using:
# - import statements
# - dir() to list functions
# - help() to read docstrings
# - Reading README.md files
#
# Skill discovery IS needed because skills are dynamic and database-backed.
# ===================================================================

def list_available_skills(api: MCPApi, category: Optional[str] = None) -> str:
    """
    List all available reusable skills.

    This function should be exposed as a tool to the agent.

    Args:
        api: MCPApi instance
        category: Optional category filter

    Returns:
        Formatted string listing all skills
    """
    skills = api.list_skills(category=category)

    if not skills:
        if category:
            return f"No skills found in category '{category}'."
        return "No skills available yet. Create your first skill when you write working code!"

    # Group by category
    by_category = {}
    for skill in skills:
        cat = skill['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(skill)

    # Format output
    result = "Available Skills:\n\n"

    for cat, cat_skills in sorted(by_category.items()):
        result += f"## {cat.replace('_', ' ').title()}\n\n"

        for skill in sorted(cat_skills, key=lambda x: x['name']):
            result += f"### {skill['name']}\n"
            result += f"**Import:** `from skills.{skill['category']}.{skill['name']} import ...`\n"

            if 'tags' in skill and skill['tags']:
                result += f"**Tags:** {', '.join(skill['tags'])}\n"

            # Read first line of README if available
            readme_path = api.skills_dir / skill['category'] / skill['name'] / 'README.md'
            if readme_path.exists():
                first_line = readme_path.read_text().split('\n')[0].replace('#', '').strip()
                if first_line:
                    result += f"**Description:** {first_line}\n"

            result += "\n"

    return result


def get_skill_categories(api: MCPApi) -> str:
    """
    Get list of available skill categories.

    This function should be exposed as a tool to the agent.

    Args:
        api: MCPApi instance

    Returns:
        Formatted string listing categories
    """
    categories = api.get_skill_categories()

    if not categories:
        return (
            "No skill categories exist yet.\n\n"
            "Common categories you can use when creating skills:\n"
            "- file_operations - File and directory manipulation\n"
            "- data_processing - Data transformation and analysis\n"
            "- api_integration - API calls and integrations\n"
            "- text_processing - Text manipulation and parsing\n"
            "- workflows - Multi-step processes\n"
            "- utilities - General helper functions\n\n"
            "Or create your own category based on the task!"
        )

    result = "Skill Categories:\n\n"

    for cat in categories:
        cat_name = cat['name'].replace('_', ' ').title()
        result += f"- **{cat_name}** ({cat['name']}): {cat['count']} skill(s)\n"

    result += "\nYou can filter skills by category or create new categories as needed."

    return result


def create_skill(api: MCPApi, code: str, name: str, category: str, tags: Optional[list] = None) -> str:
    """
    Save working code as a reusable skill.

    This function should be exposed as a tool to the agent.

    Args:
        api: MCPApi instance
        code: Python code to save
        name: Skill name (lowercase, underscores)
        category: Category name (lowercase, underscores)
        tags: Optional list of tags for discovery

    Returns:
        Success message with import path
    """
    try:
        api.save_skill(code, name, category, tags=tags)

        return (
            f"✓ Skill created: {category}/{name}\n"
            f"Import with: from skills.{category}.{name} import ...\n"
            f"The skill is immediately available for use!"
        )
    except Exception as e:
        return f"Failed to create skill: {str(e)}"


# ===================================================================
# Example Agent Integration
# ===================================================================

async def example_agent_workflow():
    """
    Example showing how an agent would use discovery tools.
    """

    # Initialize framework
    api = MCPApi(
        agent_name="example-agent",
        servers_dir="servers",
        skills_dir="skills",
        skills_db="skills.db",
        telemetry_db=None
    )

    # Hydrate skills from previous sessions
    count = await api.hydrate_skills()
    print(f"Loaded {count} skills from database\n")

    # Register an MCP server for demonstration
    api.add_mcp_server(
        name="filesystem",
        command="npx -y @modelcontextprotocol/server-filesystem /tmp"
    )

    # Generate APIs from MCP servers (one-time, commit to git)
    api.generate_libraries()

    # Start MCP runtime
    api.start()

    print("\n" + "="*70)
    print("NOTE: servers/ package is now available as regular Python imports")
    print("Agent can explore it naturally:")
    print("  - import servers.filesystem.read_file")
    print("  - help(servers.filesystem.read_file.filesystem_read_file)")
    print("  - Read servers/filesystem/read_file/README.md")
    print("="*70 + "\n")

    # ===================================================================
    # Scenario 1: Agent checks what skill categories exist
    # ===================================================================
    print("="*70)
    print("SCENARIO 1: Discover Skill Categories")
    print("="*70)

    categories_info = get_skill_categories(api)
    print(categories_info)
    print()

    # ===================================================================
    # Scenario 2: Agent lists all skills
    # ===================================================================
    print("="*70)
    print("SCENARIO 2: List All Skills")
    print("="*70)

    all_skills = list_available_skills(api)
    print(all_skills)
    print()

    # ===================================================================
    # Scenario 3: Agent creates a new skill
    # ===================================================================
    print("="*70)
    print("SCENARIO 3: Create New Skill")
    print("="*70)

    # Agent writes and tests code
    new_skill_code = '''
"""Parse CSV data into dictionary."""

def parse_csv(csv_text: str, delimiter: str = ",") -> list:
    """
    Parse CSV text into list of dictionaries.

    Args:
        csv_text: CSV formatted text
        delimiter: Field delimiter (default comma)

    Returns:
        List of dictionaries with column headers as keys
    """
    lines = csv_text.strip().split('\\n')
    if not lines:
        return []

    headers = [h.strip() for h in lines[0].split(delimiter)]

    result = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(delimiter)]
        row = dict(zip(headers, values))
        result.append(row)

    return result
'''

    # Agent saves working code
    result = create_skill(
        api,
        code=new_skill_code,
        name="parse_csv",
        category="text_processing",
        tags=["csv", "parsing", "data"]
    )
    print(result)
    print()

    # ===================================================================
    # Scenario 4: Agent filters by category
    # ===================================================================
    print("="*70)
    print("SCENARIO 4: List Skills in Specific Category")
    print("="*70)

    category_skills = list_available_skills(api, category="text_processing")
    print(category_skills)
    print()

    # ===================================================================
    # Scenario 5: Agent uses the new skill immediately
    # ===================================================================
    print("="*70)
    print("SCENARIO 5: Use New Skill Immediately")
    print("="*70)

    # Import the skill we just created
    from skills.text_processing.parse_csv import parse_csv

    test_csv = """name,age,city
Alice,30,NYC
Bob,25,SF"""

    parsed = parse_csv(test_csv)
    print(f"Parsed CSV: {parsed}")

    # Cleanup
    api.stop()


# ===================================================================
# System Prompt for Agent
# ===================================================================

AGENT_SYSTEM_PROMPT = """
You are an AI agent with access to MCP tools and reusable skills.

## Available Resources

1. **MCP Tools** (servers/ package):
   - Regular Python package with generated MCP tool wrappers
   - Functions named {server}_{tool} (e.g., filesystem_read_file)
   - Explore naturally:
     * Import: `from servers.filesystem.read_file import filesystem_read_file`
     * Introspect: `import servers.filesystem; dir(servers.filesystem)`
     * Help: `help(filesystem_read_file)`
     * Read READMEs: Each tool has servers/{server}/{tool}/README.md
   - Available in your Python environment like any package

2. **Reusable Skills** (skills/ package):
   - Code from previous sessions that worked
   - Dynamically created and database-backed
   - Use discovery tools to find existing skills
   - Use get_skill_categories() to see categories
   - Use list_available_skills() to browse skills
   - Skills are immediately available after creation

## Your Workflow

1. **Before writing code:**
   - Check if a skill exists: call list_available_skills(category="...")
   - If found, import and use it (avoid rewriting!)
   - If not, explore servers/ package for MCP tools
   - Write code using MCP tools from servers/

2. **Exploring MCP Tools:**
   - Use regular Python exploration:
     ```python
     # List available servers
     import os
     os.listdir('servers/')

     # Explore a server
     import servers.filesystem
     dir(servers.filesystem)

     # Get help on a function
     from servers.filesystem.read_file import filesystem_read_file
     help(filesystem_read_file)

     # Read documentation
     with open('servers/filesystem/read_file/README.md') as f:
         print(f.read())
     ```

3. **When you write working code:**
   - Test it thoroughly
   - Save as skill: create_skill(code, name, category, tags)
   - Choose appropriate category (see get_skill_categories())
   - Skill is immediately available for import

4. **Category Guidelines:**
   - Use existing categories when possible
   - Create new categories for distinct domains
   - Use lowercase with underscores (e.g., "data_processing")

## Discovery Tools Available

**Skill Discovery (use these tools):**
- get_skill_categories() -> List existing skill categories
- list_available_skills(category=None) -> Discover skills
  - Shows import paths and descriptions
  - Filter by category if needed

**Skill Creation:**
- create_skill(code, name, category, tags) -> Save working code
  - Immediately available for import
  - Persisted to database

## Example Workflow

User: "Count lines in /tmp/test.txt"

You:
1. Call list_available_skills(category="file_operations")
   → Check if "count_lines" skill exists
2. If yes: import and use it
3. If no:
   a. Explore servers/ package to find file tools
   b. Import filesystem_read_file from servers.filesystem.read_file
   c. Write code using that function
   d. Test it
   e. Save as skill: create_skill(code, "count_lines", "file_operations")

Remember:
- servers/ is a regular Python package (explore naturally)
- skills/ are dynamic (use discovery tools)
- Always check for existing skills before writing new code
- Save working code as skills for future reuse
"""


# ===================================================================
# Run Example
# ===================================================================

if __name__ == "__main__":
    print(AGENT_SYSTEM_PROMPT)
    print("\n")
    asyncio.run(example_agent_workflow())

"""
Generate MCP Server Wrappers

This script generates Python wrapper functions for MCP servers.
Run this ONCE (or whenever you add/change MCP servers) to generate
the servers/ package that your agent will import.

Workflow:
1. Edit this file to configure your MCP servers
2. Run: python generate_servers.py
3. Commit servers/ to git with your agent code
4. Your agent can now import from servers/

Example:
    python generate_servers.py
    # → Creates servers/ directory with generated wrappers

    git add servers/
    git commit -m "Add MCP server wrappers"

    # Now your agent can use:
    # from servers.filesystem.read_file import filesystem_read_file
"""

from pathlib import Path
from src import MCPApi


def main():
    """Generate MCP server wrappers."""

    # Initialize API (agent_name not important for codegen)
    api = MCPApi(
        agent_name="codegen",
        servers_dir="servers",
        skills_dir="skills",  # Not used for codegen
        skills_db="skills.db"  # Not used for codegen
    )

    print("=" * 70)
    print("MCP Server Wrapper Generator")
    print("=" * 70)
    print()

    # ===================================================================
    # Configure your MCP servers here
    # ===================================================================

    print("Registering MCP servers...")

    # Example: Filesystem server
    api.add_mcp_server(
        name="filesystem",
        command="npx -y @modelcontextprotocol/server-filesystem /tmp"
    )
    print("  ✓ Registered: filesystem")

    # Example: GitHub server
    # api.add_mcp_server(
    #     name="github",
    #     command="npx -y @modelcontextprotocol/server-github"
    # )
    # print("  ✓ Registered: github")

    # Example: Google Drive server
    # api.add_mcp_server(
    #     name="google_drive",
    #     command="npx -y @modelcontextprotocol/server-google-drive"
    # )
    # print("  ✓ Registered: google_drive")

    # Add more servers as needed...

    print()

    # ===================================================================
    # Generate Python wrappers
    # ===================================================================

    print("Generating Python wrappers...")
    api.generate_libraries()

    print()
    print("=" * 70)
    print("✓ Code generation complete!")
    print("=" * 70)
    print()
    print("Generated servers/ package with Python wrappers")
    print()
    print("Next steps:")
    print("  1. Review the generated code in servers/")
    print("  2. Commit to git:")
    print("     git add servers/")
    print("     git commit -m 'Add MCP server wrappers'")
    print()
    print("  3. Your agent can now import from servers/:")
    print("     from servers.filesystem.read_file import filesystem_read_file")
    print()
    print("Re-run this script anytime you add/change MCP servers.")
    print()


if __name__ == "__main__":
    main()

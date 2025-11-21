"""
CLI tools for MCP Skill Framework.

Provides command-line utilities for developers to generate MCP server wrappers.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List
from src import MCPApi


def generate_servers(
    servers: List[Dict[str, str]],
    servers_dir: str = "servers",
    verbose: bool = True
) -> None:
    """
    Generate Python wrapper libraries from MCP server configurations.

    Args:
        servers: List of server configurations, each with 'name' and 'command'
        servers_dir: Directory where generated code will be written
        verbose: Print progress messages
    """
    if verbose:
        print("=" * 70)
        print("MCP Server Wrapper Generator")
        print("=" * 70)
        print()

    # Initialize API (agent_name not important for codegen)
    api = MCPApi(
        agent_name="codegen",
        servers_dir=servers_dir,
        skills_dir="skills",  # Not used for codegen
        skills_db="skills.db",  # Not used for codegen
        telemetry_db=None  # Disable telemetry for codegen
    )

    if verbose:
        print("Registering MCP servers...")

    # Register all servers
    for server_config in servers:
        name = server_config.get("name")
        command = server_config.get("command")

        if not name or not command:
            print(f"  ✗ Skipped invalid config: {server_config}", file=sys.stderr)
            continue

        api.add_mcp_server(name=name, command=command)
        if verbose:
            print(f"  ✓ Registered: {name}")

    if verbose:
        print()
        print("Generating Python wrappers...")

    # Generate code
    api.generate_libraries()

    if verbose:
        print()
        print("=" * 70)
        print("✓ Code generation complete!")
        print("=" * 70)
        print()
        print(f"Generated {servers_dir}/ package with Python wrappers")
        print()
        print("Next steps:")
        print(f"  1. Review the generated code in {servers_dir}/")
        print("  2. Commit to git:")
        print(f"     git add {servers_dir}/")
        print("     git commit -m 'Add MCP server wrappers'")
        print()
        print(f"  3. Your agent can now import from {servers_dir}/:")
        print(f"     from {servers_dir}.filesystem.read_file import filesystem_read_file")
        print()


def generate_command(args: argparse.Namespace) -> int:
    """Execute the generate command."""
    # Import here to avoid circular imports
    import json

    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        print()
        print("Create a config file (e.g., mcp-servers.json) with this format:")
        print(json.dumps({
            "servers": [
                {
                    "name": "filesystem",
                    "command": "npx -y @modelcontextprotocol/server-filesystem /tmp"
                },
                {
                    "name": "github",
                    "command": "npx -y @modelcontextprotocol/server-github"
                }
            ]
        }, indent=2))
        return 1

    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        return 1

    servers = config.get("servers", [])

    if not servers:
        print("Error: No servers configured in config file", file=sys.stderr)
        return 1

    try:
        generate_servers(
            servers=servers,
            servers_dir=args.output,
            verbose=not args.quiet
        )
        return 0
    except Exception as e:
        print(f"Error during generation: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Python wrapper libraries from MCP servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from config file
  mcp-generate mcp-servers.json

  # Specify output directory
  mcp-generate mcp-servers.json --output my-servers

  # Quiet mode
  mcp-generate mcp-servers.json --quiet

Config file format (JSON):
  {
    "servers": [
      {
        "name": "filesystem",
        "command": "npx -y @modelcontextprotocol/server-filesystem /tmp"
      },
      {
        "name": "github",
        "command": "npx -y @modelcontextprotocol/server-github"
      }
    ]
  }
        """
    )

    parser.add_argument(
        "config",
        help="Path to JSON config file with MCP server definitions"
    )

    parser.add_argument(
        "-o", "--output",
        default="servers",
        help="Output directory for generated code (default: servers)"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed error messages"
    )

    args = parser.parse_args()

    return generate_command(args)


if __name__ == "__main__":
    sys.exit(main())

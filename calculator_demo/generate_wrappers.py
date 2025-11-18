#!/usr/bin/env python3
"""
Generate MCP wrappers for calculator server.
Workaround for async context issues in CLI.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_skill_framework import MCPApi

def main():
    print("🔧 Generating MCP wrapper libraries...")
    print()

    # Initialize API
    api = MCPApi(
        agent_name="codegen",
        servers_dir="servers",
        skills_dir="skills_temp",  # Not used for codegen
        skills_db="temp.db",  # Not used for codegen
        telemetry_db=None,
    )

    # Register calculator server
    print("📝 Registering calculator server...")
    api.add_mcp_server(
        name="calculator",
        command=f"python {os.path.join(os.getcwd(), 'calculator_server.py')}",
    )

    # Generate libraries
    print("⚙️  Generating Python wrappers...")
    try:
        api.generate_libraries()
        print()
        print("✅ MCP wrappers generated successfully!")
        print("📁 Check the servers/ directory for generated code")
        print()

        # List generated tools
        print("Generated tools:")
        servers_dir = Path("servers/calculator")
        if servers_dir.exists():
            tools = [d.name for d in servers_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
            for tool in sorted(tools):
                print(f"  - {tool}")
        print()
        return 0
    except Exception as e:
        print()
        print(f"❌ Failed to generate MCP wrappers: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

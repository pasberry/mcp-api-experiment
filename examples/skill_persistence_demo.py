"""
Skill Persistence Demo

This example demonstrates the skill persistence and hydration workflow:
1. Creating skills in one session
2. Skills are persisted to SQLite database
3. Restoring skills in a new session via hydration
4. Multiple agents sharing the same database
"""

import asyncio
import logging
from pathlib import Path
import shutil
from src import MCPApi

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


async def session_1():
    """First session: Create and save skills."""
    print("\n" + "="*70)
    print("SESSION 1: Agent creates skills")
    print("="*70)

    # Initialize API for agent-1
    api = MCPApi(
        agent_name="agent-1",
        servers_dir="demo_servers",
        skills_dir="demo_skills",
        skills_db="demo_skills.db",
        telemetry_db=None  # Disable telemetry for demo
    )

    # Add a simple MCP server
    print("\n[1] Setting up MCP server...")
    api.add_mcp_server(
        name="demo_server",
        command="echo 'Demo MCP Server'"
    )

    # Generate libraries
    print("[2] Generating Python libraries...")
    api.generate_libraries()

    # Create some skills
    print("\n[3] Creating skills...")

    skill1 = '''
"""Process data from multiple sources."""

def process_data(sources):
    """
    Process data from multiple sources.

    Args:
        sources: List of data sources

    Returns:
        Processed results
    """
    results = []
    for source in sources:
        # Process each source
        results.append({"source": source, "status": "processed"})
    return results
'''

    api.save_skill(
        code=skill1,
        name="process_data",
        category="data_processing",
        tags=["batch", "processing"]
    )
    print("  ✓ Saved: data_processing/process_data")

    skill2 = '''
"""Aggregate results from processing."""

def aggregate_results(results):
    """
    Aggregate processing results.

    Args:
        results: List of processing results

    Returns:
        Aggregated summary
    """
    total = len(results)
    successful = sum(1 for r in results if r.get("status") == "processed")
    return {
        "total": total,
        "successful": successful,
        "success_rate": successful / total if total > 0 else 0
    }
'''

    api.save_skill(
        code=skill2,
        name="aggregate_results",
        category="data_processing",
        tags=["aggregation", "summary"]
    )
    print("  ✓ Saved: data_processing/aggregate_results")

    # Wait a moment for async DB writes to complete
    await asyncio.sleep(0.5)

    # Show what's in filesystem
    print("\n[4] Filesystem state:")
    skills = api.list_skills()
    print(f"  Skills in filesystem: {len(skills)}")
    for skill in skills:
        print(f"    - {skill['category']}/{skill['name']}")

    # Show what's in database
    print("\n[5] Database state:")
    stats = await api.get_skill_stats()
    print(f"  Agent: {stats['agent_name']}")
    print(f"  Total skills in DB: {stats['total_skills']}")
    for category, count in stats['by_category'].items():
        print(f"    - {category}: {count} skills")

    api.stop()
    print("\n[6] Session 1 complete - skills persisted to database")


async def session_2():
    """Second session: Hydrate skills from database."""
    print("\n" + "="*70)
    print("SESSION 2: New agent session - hydrate from database")
    print("="*70)

    # Simulate agent restart: clear the skills directory
    print("\n[1] Simulating agent restart...")
    skills_dir = Path("demo_skills")
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
        print("  ✓ Cleared skills directory (simulating fresh start)")

    # Initialize API again (same agent)
    api = MCPApi(
        agent_name="agent-1",
        servers_dir="demo_servers",
        skills_dir="demo_skills",
        skills_db="demo_skills.db",
        telemetry_db=None
    )

    # Check filesystem before hydration
    print("\n[2] Filesystem state BEFORE hydration:")
    skills_before = api.list_skills()
    print(f"  Skills in filesystem: {len(skills_before)}")

    # Hydrate skills from database
    print("\n[3] Hydrating skills from database...")
    count = await api.hydrate_skills()
    print(f"  ✓ Hydrated {count} skills from database")

    # Check filesystem after hydration
    print("\n[4] Filesystem state AFTER hydration:")
    skills_after = api.list_skills()
    print(f"  Skills in filesystem: {len(skills_after)}")
    for skill in skills_after:
        print(f"    - {skill['category']}/{skill['name']}")
        # Verify files exist
        skill_dir = Path(f"demo_skills/{skill['category']}/{skill['name']}")
        if (skill_dir / "main.py").exists():
            print(f"      ✓ main.py exists")
        if (skill_dir / "README.md").exists():
            print(f"      ✓ README.md exists")

    # Verify we can read skill code
    print("\n[5] Reading skill from filesystem:")
    skill_info = api.get_skill_info("data_processing", "process_data")
    print(f"  Name: {skill_info['name']}")
    print(f"  Category: {skill_info['category']}")
    print(f"  Dependencies: {len(skill_info.get('dependencies', []))}")
    print(f"  Code lines: {len(skill_info['code'].split(chr(10)))}")

    api.stop()
    print("\n[6] Session 2 complete - skills successfully hydrated!")


async def session_3():
    """Third session: Different agent using same database."""
    print("\n" + "="*70)
    print("SESSION 3: Different agent using same database")
    print("="*70)

    # Initialize API for agent-2 (different agent, same database)
    api = MCPApi(
        agent_name="agent-2",
        servers_dir="demo_servers",
        skills_dir="demo_skills_agent2",
        skills_db="demo_skills.db",  # Same database!
        telemetry_db=None
    )

    # Create a skill for agent-2
    print("\n[1] Agent-2 creating its own skill...")
    skill3 = '''
"""Format data for output."""

def format_output(data):
    """Format data for display."""
    return f"Result: {data}"
'''

    api.save_skill(
        code=skill3,
        name="format_output",
        category="formatting",
        tags=["output", "display"]
    )
    print("  ✓ Saved: formatting/format_output")

    await asyncio.sleep(0.5)  # Wait for async DB write

    # Show agent-2's stats
    print("\n[2] Agent-2 database stats:")
    stats = await api.get_skill_stats()
    print(f"  Agent: {stats['agent_name']}")
    print(f"  Total skills: {stats['total_skills']}")

    # Compare with agent-1's stats (using same database)
    api_agent1 = MCPApi(
        agent_name="agent-1",
        servers_dir="demo_servers",
        skills_dir="demo_skills",
        skills_db="demo_skills.db",
        telemetry_db=None
    )

    print("\n[3] Agent-1 database stats (from same database):")
    stats1 = await api_agent1.get_skill_stats()
    print(f"  Agent: {stats1['agent_name']}")
    print(f"  Total skills: {stats1['total_skills']}")

    print("\n[4] Multi-agent isolation demonstrated:")
    print(f"  ✓ Agent-1 has {stats1['total_skills']} skills")
    print(f"  ✓ Agent-2 has {stats['total_skills']} skill")
    print(f"  ✓ Both stored in same database, isolated by agent_name")

    api.stop()
    api_agent1.stop()


async def cleanup():
    """Clean up demo files."""
    print("\n" + "="*70)
    print("CLEANUP")
    print("="*70)

    # Remove demo directories and database
    paths_to_remove = [
        Path("demo_servers"),
        Path("demo_skills"),
        Path("demo_skills_agent2"),
        Path("demo_skills.db")
    ]

    for path in paths_to_remove:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"  ✓ Removed {path}")

    print("\nDemo complete!")


async def main():
    """Run the complete demo."""
    print("\n" + "="*70)
    print("SKILL PERSISTENCE & HYDRATION DEMO")
    print("="*70)
    print("\nThis demo shows:")
    print("  1. Creating skills and persisting to database")
    print("  2. Hydrating skills from database in a new session")
    print("  3. Multiple agents sharing the same database")
    print("="*70)

    try:
        # Run three sessions
        await session_1()
        await session_2()
        await session_3()
    finally:
        # Always cleanup
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())

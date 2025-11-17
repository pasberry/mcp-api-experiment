"""
Test telemetry logging functionality.

This script verifies that telemetry is properly integrated into:
- Code execution
- Skill saving (with dependency detection)
- Metrics aggregation

Note: MCP call telemetry requires actual MCP servers, so we skip that here.
"""

import asyncio
from pathlib import Path
from mcp_skill_framework import MCPApi
import json


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print('='*70)


def main():
    print_section("TELEMETRY INTEGRATION TEST")

    # Initialize MCPApi with telemetry enabled
    print("\nInitializing MCPApi with telemetry...")
    api = MCPApi(
        servers_dir="test_servers",
        skills_dir="test_skills",
        tasks_dir="test_tasks",
        use_docker=False,  # Use subprocess for faster testing
        telemetry_db=".test_telemetry/telemetry.db"
    )

    try:
        # Start the API (no MCP servers for this test)
        print("Starting API...")
        api.start()

        # Test 1: Execute successful code
        print_section("TEST 1: Execute Successful Code")
        code1 = """
# Calculate fibonacci numbers
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

result = [fib(i) for i in range(10)]
print(f"Fibonacci numbers: {result}")
"""
        print("Executing code...")
        result1 = api.execute(code1)
        print(f"Success: {result1['success']}")
        print(f"Return value: {result1.get('return_value')}")

        # Test 2: Execute code with error
        print_section("TEST 2: Execute Code with Error")
        code2 = """
# This will cause a division by zero error
x = 10
y = 0
result = x / y
"""
        print("Executing code with error...")
        result2 = api.execute(code2)
        print(f"Success: {result2['success']}")
        if not result2['success']:
            print(f"Error type: {result2['error']['type']}")
            print(f"Error message: {result2['error']['message']}")
            print(f"Line number: {result2['error']['line_number']}")

        # Test 3: Save skill with dependencies
        print_section("TEST 3: Save Skill with Dependencies")
        skill_code = """
\"\"\"
Data synchronization skill.

Syncs files from Google Drive to local storage.
\"\"\"

def sync_files(folder_id):
    # List files from Google Drive
    files = mcp_call('google-drive', 'list_files', {'folder_id': folder_id})

    # Download each file
    for file in files:
        content = mcp_call('google-drive', 'download_file', {'file_id': file['id']})

        # Save locally
        with open(file['name'], 'wb') as f:
            f.write(content)

    return len(files)
"""
        print("Saving skill...")
        api.save_skill(
            code=skill_code,
            name="sync_files",
            category="data_sync"
        )
        print("Skill saved successfully")

        # Test 4: Get telemetry metrics
        print_section("TEST 4: Telemetry Metrics")
        metrics = api.get_metrics()

        print(f"\nTelemetry enabled: {metrics['telemetry_enabled']}")

        print("\n--- Code Execution Metrics ---")
        health = metrics['health_snapshot']
        for entry in health['metrics']:
            if entry['event_type'] == 'code_execution':
                print(f"  Total executions: {entry['total']}")
                print(f"  Successful: {entry['successful']}")
                print(f"  Failed: {entry['failed']}")
                print(f"  Success rate: {entry['success_rate_pct']}%")
                print(f"  Avg duration: {entry['avg_duration_ms']}ms")

        print("\n--- Error Patterns ---")
        errors = metrics['error_patterns']
        if errors:
            for error in errors:
                print(f"  {error['error_type']} ({error['event_type']}): {error['occurrences']} occurrences")
        else:
            print("  (Error patterns will show in error_patterns after errors occur)")

        # Test 5: Query telemetry database directly
        print_section("TEST 5: Direct Database Query")
        if api.telemetry:
            # Get all events
            cursor = api.telemetry.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM events")
            total_events = cursor.fetchone()['count']
            print(f"Total events logged: {total_events}")

            # Get events by type
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM events
                GROUP BY event_type
                ORDER BY count DESC
            """)
            print("\nEvents by type:")
            for row in cursor.fetchall():
                print(f"  {row['event_type']}: {row['count']}")

            # Show skill save event with dependencies
            cursor.execute("""
                SELECT skill_category, skill_name, data
                FROM events
                WHERE event_type = 'skill_save'
            """)
            print("\nSkill save events:")
            for row in cursor.fetchall():
                data = json.loads(row['data'])
                print(f"  {row['skill_category']}/{row['skill_name']}")
                print(f"    Code lines: {data['code_lines']}")
                print(f"    Dependencies: {json.dumps(data['dependencies'], indent=6)}")

        # Test 6: Verify skills directory has metadata with dependencies
        print_section("TEST 6: Skill Metadata Verification")
        skill_meta_path = Path("test_skills/data_sync/sync_files/.meta.json")
        if skill_meta_path.exists():
            with open(skill_meta_path) as f:
                metadata = json.load(f)
            print(f"Skill: {metadata['name']}")
            print(f"Category: {metadata['category']}")
            print(f"Dependencies detected:")
            for dep in metadata['dependencies']:
                print(f"  - {dep['server']}.{dep['tool']}")
        else:
            print("Skill metadata not found")

        print_section("ALL TESTS COMPLETED")
        print("\nTelemetry database location: .test_telemetry/telemetry.db")
        print("You can query it with: sqlite3 .test_telemetry/telemetry.db")
        print("\nOr use the SQL queries in sql/ folder:")
        print("  sqlite3 .test_telemetry/telemetry.db < sql/health_snapshot.sql")

    finally:
        # Clean up
        api.stop()
        if api.telemetry:
            api.telemetry.close()


if __name__ == "__main__":
    main()

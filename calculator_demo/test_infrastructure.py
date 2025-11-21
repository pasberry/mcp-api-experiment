#!/usr/bin/env python3
"""
Test the MCP Skill Framework infrastructure without needing API keys.

This verifies:
1. Generated wrappers can be imported
2. MCP runtime connects to calculator server
3. Calculator operations work
4. Skills can be saved to filesystem and database
"""
import sys
import os
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import MCPApi

def test_generated_wrappers():
    """Test that generated wrappers can be imported."""
    print("=" * 60)
    print("TEST 1: Importing Generated Wrappers")
    print("=" * 60)

    try:
        from servers.calculator.add import calculator_add
        from servers.calculator.subtract import calculator_subtract
        from servers.calculator.multiply import calculator_multiply
        from servers.calculator.divide import calculator_divide

        print("✅ All calculator wrappers imported successfully")
        print(f"  - calculator_add: {calculator_add.__name__}")
        print(f"  - calculator_subtract: {calculator_subtract.__name__}")
        print(f"  - calculator_multiply: {calculator_multiply.__name__}")
        print(f"  - calculator_divide: {calculator_divide.__name__}")
        return True
    except Exception as e:
        print(f"❌ Failed to import wrappers: {e}")
        return False


def test_mcp_runtime():
    """Test that MCP runtime can connect and call tools."""
    print("\n" + "=" * 60)
    print("TEST 2: MCP Runtime Connection & Tool Calls")
    print("=" * 60)

    try:
        # Initialize API
        api = MCPApi(
            agent_name="test-agent",
            servers_dir="servers",
            skills_dir="skills_test",
            skills_db="test_skills.db",
            telemetry_db=None,
        )

        # Register calculator server
        print("📝 Registering calculator server...")
        api.add_mcp_server(
            name="calculator",
            command=f"python {os.path.join(os.getcwd(), 'calculator_server.py')}",
        )

        # Start runtime
        print("🚀 Starting MCP runtime...")
        api.start()

        # Import and test calculator functions
        from servers.calculator.add import calculator_add
        from servers.calculator.divide import calculator_divide

        print("\n🧮 Testing calculator operations...")

        # Test: 5 + 3
        print("  Testing: 5 + 3")
        result_json = calculator_add(a=5, b=3)
        result = json.loads(result_json)
        assert result["result"] == 8, f"Expected 8, got {result['result']}"
        print(f"  ✅ Result: {result['result']}")

        # Test: 10 / 2
        print("  Testing: 10 / 2")
        result_json = calculator_divide(a=10, b=2)
        result = json.loads(result_json)
        assert result["result"] == 5, f"Expected 5, got {result['result']}"
        print(f"  ✅ Result: {result['result']}")

        # Stop runtime
        api.stop()

        print("\n✅ MCP runtime test passed")
        return True

    except Exception as e:
        print(f"\n❌ MCP runtime test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_persistence():
    """Test that skills can be saved to filesystem and database."""
    print("\n" + "=" * 60)
    print("TEST 3: Skill Persistence")
    print("=" * 60)

    try:
        # Initialize API
        api = MCPApi(
            agent_name="test-agent",
            servers_dir="servers",
            skills_dir="skills_test",
            skills_db="test_skills.db",
            telemetry_db=None,
        )

        # Register and start
        api.add_mcp_server(
            name="calculator",
            command=f"python {os.path.join(os.getcwd(), 'calculator_server.py')}",
        )
        api.start()

        # Create a skill that uses the calculator
        skill_code = '''"""
Calculate sum of three numbers
"""
import json
from servers.calculator.add import calculator_add

# Add first two numbers
result1_json = calculator_add(a=3, b=3)
result1 = json.loads(result1_json)["result"]

# Add third number
result2_json = calculator_add(a=result1, b=3)
result2 = json.loads(result2_json)["result"]

print(f"Answer: {result2}")
'''

        print("💾 Saving skill: 'add_three_numbers'...")
        api.save_skill(
            code=skill_code,
            name="add_three_numbers",
            category="math_operations",
            tags=["math", "calculator", "test"],
            persist_to_db=True,
        )

        # Check filesystem
        skill_path = Path("skills_test/math_operations/add_three_numbers/__init__.py")
        assert skill_path.exists(), "Skill not saved to filesystem"
        print(f"  ✅ Skill saved to: {skill_path}")

        # Check database (async)
        import asyncio
        async def check_db():
            stats = await api.get_skill_stats()
            return stats

        stats = asyncio.run(check_db())
        assert stats["total_skills"] >= 1, "Skill not in database"
        print(f"  ✅ Database has {stats['total_skills']} skill(s)")

        # Stop runtime
        api.stop()

        print("\n✅ Skill persistence test passed")
        return True

    except Exception as e:
        print(f"\n❌ Skill persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all infrastructure tests."""
    print("\n" + "=" * 60)
    print("🧪 MCP SKILL FRAMEWORK INFRASTRUCTURE TESTS")
    print("=" * 60)
    print("\nThis verifies the core framework without needing API keys.\n")

    results = []

    # Test 1: Generated wrappers
    results.append(("Generated Wrappers", test_generated_wrappers()))

    # Test 2: MCP Runtime
    results.append(("MCP Runtime", test_mcp_runtime()))

    # Test 3: Skill Persistence
    results.append(("Skill Persistence", test_skill_persistence()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All infrastructure tests passed!")
        print("\nThe MCP Skill Framework is working correctly.")
        print("You can now run the full agent demo with:")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("  python math_agent.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

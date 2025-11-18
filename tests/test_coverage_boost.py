"""
Additional targeted tests to reach 80% coverage.

Tests for uncovered methods and edge cases in database, framework, and skill_manager.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_skill_framework import MCPApi, SkillsDatabase, SkillManager


class TestDatabaseUpdateAndDelete:
    """Test database UPDATE and DELETE operations."""

    @pytest.mark.asyncio
    async def test_save_skill_updates_existing(self):
        """Test that saving an existing skill updates it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save initial skill
            await db.save_skill(
                agent_name="test-agent",
                skill_name="my_skill",
                category="v1",
                code="def v1(): pass",
            )

            # Update the same skill
            await db.save_skill(
                agent_name="test-agent",
                skill_name="my_skill",  # Same name
                category="v2",  # Different category
                code="def v2(): pass",  # Different code
            )

            # Verify it was updated, not duplicated
            skills = await db.get_all_skills("test-agent")
            assert len(skills) == 1  # Only one skill
            assert skills[0]["category"] == "v2"  # Updated category
            assert skills[0]["code"] == "def v2(): pass"  # Updated code

    @pytest.mark.asyncio
    async def test_delete_skill_success(self):
        """Test deleting an existing skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save a skill
            await db.save_skill(
                agent_name="test-agent",
                skill_name="to_delete",
                category="test",
                code="def test(): pass",
            )

            # Delete it
            deleted = await db.delete_skill("test-agent", "to_delete")

            assert deleted is True

            # Verify it's gone
            skill = await db.get_skill("test-agent", "to_delete")
            assert skill is None

    @pytest.mark.asyncio
    async def test_delete_skill_not_found(self):
        """Test deleting a non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Try to delete non-existent skill
            deleted = await db.delete_skill("test-agent", "nonexistent")

            assert deleted is False


class TestFrameworkStopMethod:
    """Test framework stop() method."""

    def test_stop_disconnects_when_started(self):
        """Test that stop() disconnects when runtime is started."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            # Mark as started
            api._started = True

            with patch.object(api.connector, "disconnect_all") as mock_disconnect:
                with patch.object(api.runtime, "clear") as mock_clear:
                    api.stop()

                    mock_disconnect.assert_called_once()
                    mock_clear.assert_called_once()
                    assert api._started is False

    def test_stop_does_nothing_when_not_started(self):
        """Test that stop() does nothing if not started."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            # Not started
            api._started = False

            with patch.object(api.connector, "disconnect_all") as mock_disconnect:
                api.stop()

                # Should not call disconnect if not started
                mock_disconnect.assert_not_called()

    def test_start_idempotent(self):
        """Test that calling start() twice doesn't re-connect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.connector, "connect_all") as mock_connect:
                with patch.object(api.connector, "get_connections") as mock_get:
                    mock_get.return_value = {}

                    # First start
                    api.start()
                    assert api._started is True
                    assert mock_connect.call_count == 1

                    # Second start - should be no-op
                    api.start()
                    assert mock_connect.call_count == 1  # Still just 1 call


class TestFrameworkAdditionalMethods:
    """Test additional framework methods."""

    def test_get_metrics(self):
        """Test get_metrics() returns metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            # Should return disabled message when no telemetry
            metrics = api.get_metrics()

            assert "telemetry_enabled" in metrics
            assert metrics["telemetry_enabled"] is False
            assert metrics["message"] == "Telemetry is disabled"

    def test_list_mcp_tools(self):
        """Test list_mcp_tools() delegates to connector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.connector, "list_tools") as mock_list:
                mock_list.return_value = [{"name": "test_tool"}]

                result = api.list_mcp_tools()

                assert result == [{"name": "test_tool"}]
                mock_list.assert_called_once_with(server=None)

    def test_list_mcp_tools_with_server_filter(self):
        """Test list_mcp_tools() with server filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.connector, "list_tools") as mock_list:
                api.list_mcp_tools(server="filesystem")

                mock_list.assert_called_once_with(server="filesystem")

    def test_list_servers(self):
        """Test list_servers() delegates to connector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.connector, "list_servers") as mock_list:
                mock_list.return_value = [{"name": "filesystem", "connected": False}]

                result = api.list_servers()

                assert result == [{"name": "filesystem", "connected": False}]
                mock_list.assert_called_once()


class TestSkillManagerDatabaseStats:
    """Test skill_manager get_database_stats() method."""

    @pytest.mark.asyncio
    async def test_get_database_stats(self):
        """Test getting database statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            # Setup database with skills
            db = SkillsDatabase(db_path)
            await db.initialize()

            await db.save_skill("test-agent", "skill1", "cat1", "pass")
            await db.save_skill("test-agent", "skill2", "cat1", "pass")
            await db.save_skill("test-agent", "skill3", "cat2", "pass")

            # Create manager
            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            # Get stats
            stats = await manager.get_database_stats()

            assert stats["total_skills"] == 3
            assert stats["by_category"]["cat1"] == 2
            assert stats["by_category"]["cat2"] == 1


class TestFrameworkContextManager:
    """Test framework context manager support."""

    def test_context_manager_enter_exit(self):
        """Test __enter__ and __exit__ context manager methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("mcp_skill_framework.framework.MCPConnector") as MockConnector:
                # Setup mocks
                mock_connector = MockConnector.return_value
                mock_connector.connect_all = MagicMock()
                mock_connector.disconnect_all = MagicMock()
                mock_connector.get_connections = MagicMock(return_value={})

                api = MCPApi(
                    agent_name="test-agent",
                    servers_dir=f"{tmpdir}/servers",
                    skills_dir=f"{tmpdir}/skills",
                    skills_db=f"{tmpdir}/skills.db",
                    telemetry_db=None,
                )

                # Use as context manager
                with api as ctx_api:
                    assert ctx_api is api
                    assert api._started is True

                # After exit, should be stopped
                assert api._started is False

    def test_context_manager_with_telemetry(self):
        """Test __exit__ closes telemetry when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_db = f"{tmpdir}/telemetry.db"

            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=telemetry_db,
            )

            # Mock telemetry close
            with patch.object(api.telemetry, "close") as mock_close:
                with patch.object(api, "start"):
                    with patch.object(api, "stop"):
                        with api:
                            pass

                        # Telemetry should be closed on exit
                        mock_close.assert_called_once()

    def test_get_metrics_with_telemetry_enabled(self):
        """Test get_metrics() when telemetry is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_db = f"{tmpdir}/telemetry.db"

            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=telemetry_db,
            )

            # Mock telemetry methods
            with patch.object(api.telemetry, "get_tool_metrics") as mock_tool_metrics:
                with patch.object(api.telemetry, "get_health_snapshot") as mock_health:
                    mock_tool_metrics.return_value = {"filesystem_read_file": {"count": 5}}
                    mock_health.return_value = {"total_calls": 10}

                    metrics = api.get_metrics()

                    assert metrics["telemetry_enabled"] is True
                    assert "tool_metrics" in metrics
                    assert "health_snapshot" in metrics
                    assert metrics["tool_metrics"] == {"filesystem_read_file": {"count": 5}}


class TestDatabaseAdditional:
    """Test additional database edge cases."""

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize() is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)

            # Initialize once
            await db.initialize()

            # Initialize again - should return early without errors
            await db.initialize()

            # Should still work normally
            await db.save_skill("test-agent", "skill1", "cat1", "pass")
            skills = await db.get_all_skills("test-agent")
            assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_get_all_skills_with_dependencies(self):
        """Test retrieving skills with dependencies JSON field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save skill with dependencies
            await db.save_skill(
                agent_name="test-agent",
                skill_name="complex",
                category="test",
                code="def test(): pass",
                dependencies=[{"server": "fs", "tool": "read"}],
            )

            # Retrieve and verify dependencies are parsed
            skills = await db.get_all_skills("test-agent")
            assert len(skills) == 1
            assert "dependencies" in skills[0]
            assert isinstance(skills[0]["dependencies"], list)
            assert skills[0]["dependencies"] == [{"server": "fs", "tool": "read"}]

    @pytest.mark.asyncio
    async def test_get_all_skills_with_metadata(self):
        """Test retrieving skills with metadata JSON field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save skill with metadata
            await db.save_skill(
                agent_name="test-agent",
                skill_name="complex",
                category="test",
                code="def test(): pass",
                metadata={"version": "1.0", "author": "test"},
            )

            # Retrieve and verify metadata is parsed
            skills = await db.get_all_skills("test-agent")
            assert len(skills) == 1
            assert "metadata" in skills[0]
            assert isinstance(skills[0]["metadata"], dict)
            assert skills[0]["metadata"] == {"version": "1.0", "author": "test"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

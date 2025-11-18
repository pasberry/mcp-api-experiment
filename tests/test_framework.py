"""
Tests for MCPApi framework integration.

Tests the main MCPApi class that orchestrates code generation and skill management.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from mcp_skill_framework import MCPApi


class TestMCPApiInitialization:
    """Test MCPApi initialization."""

    def test_api_basic_initialization(self):
        """Test basic API initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,  # Disable telemetry for this test
            )

            assert api.agent_name == "test-agent"
            assert api.servers_dir == Path(f"{tmpdir}/servers")
            assert api.skills_dir == Path(f"{tmpdir}/skills")
            assert api._started is False
            assert api.telemetry is None

    def test_api_creates_directories(self):
        """Test that API creates necessary directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            servers_dir = Path(tmpdir) / "servers"
            skills_dir = Path(tmpdir) / "skills"

            assert not servers_dir.exists()
            assert not skills_dir.exists()

            api = MCPApi(
                agent_name="test-agent",
                servers_dir=str(servers_dir),
                skills_dir=str(skills_dir),
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            assert servers_dir.exists()
            assert skills_dir.exists()

    def test_api_with_telemetry_enabled(self):
        """Test API initialization with telemetry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_db = Path(tmpdir) / "telemetry.db"

            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=str(telemetry_db),
            )

            assert api.telemetry is not None


class TestAddMCPServer:
    """Test add_mcp_server() method."""

    def test_add_single_server(self):
        """Test adding a single MCP server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            api.add_mcp_server("test_server", "echo test")

            assert "test_server" in api.connector.servers

    def test_add_multiple_servers(self):
        """Test adding multiple servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            api.add_mcp_server("server1", "echo test1")
            api.add_mcp_server("server2", "echo test2")
            api.add_mcp_server("server3", "echo test3")

            assert len(api.connector.servers) == 3

    def test_add_server_with_env(self):
        """Test adding server with environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            env = {"API_KEY": "secret"}
            api.add_mcp_server("github", "npx server-github", env=env)

            assert api.connector.servers["github"]["env"] == env


class TestGenerateLibraries:
    """Test generate_libraries() method."""

    def test_generate_libraries_calls_connector(self):
        """Test that generate_libraries delegates to connector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            # Mock the connector methods
            with patch.object(api.connector, "connect_all") as mock_connect:
                with patch.object(api.connector, "generate_apis") as mock_generate:
                    with patch.object(api.connector, "disconnect_all") as mock_disconnect:
                        api.generate_libraries()

                        # Verify connector was called
                        mock_connect.assert_called_once()
                        mock_generate.assert_called_once_with(output_dir=api.servers_dir)
                        mock_disconnect.assert_called_once()


class TestStartMethod:
    """Test start() method for runtime."""

    def test_start_registers_connections(self):
        """Test that start() sets up runtime connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            # Mock connector methods
            with patch.object(api.connector, "connect_all"):
                with patch.object(api.connector, "get_connections") as mock_get_conn:
                    mock_connections = {"test_server": MagicMock()}
                    mock_get_conn.return_value = mock_connections

                    with patch.object(api.runtime, "register_servers") as mock_register:
                        api.start()

                        # Verify runtime was registered
                        mock_register.assert_called_once_with(mock_connections)
                        assert api._started is True


class TestSaveSkill:
    """Test save_skill() method."""

    def test_save_skill_delegates_to_manager(self):
        """Test that save_skill delegates to skill manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            code = "def test(): pass"
            name = "test_skill"
            category = "test"
            tags = ["test"]

            with patch.object(api.skill_manager, "save_skill") as mock_save:
                api.save_skill(code, name, category, tags=tags)

                mock_save.assert_called_once_with(
                    code=code,
                    name=name,
                    category=category,
                    tags=tags,
                    persist_to_db=True,
                )

    def test_save_skill_with_persist_false(self):
        """Test save_skill with persist_to_db=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.skill_manager, "save_skill") as mock_save:
                api.save_skill("code", "name", "category", persist_to_db=False)

                # Check persist_to_db was passed
                call_args = mock_save.call_args[1]
                assert call_args["persist_to_db"] is False


class TestHydrateSkills:
    """Test hydrate_skills() method."""

    @pytest.mark.asyncio
    async def test_hydrate_skills_delegates_to_manager(self):
        """Test that hydrate_skills delegates to skill manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.skill_manager, "hydrate_from_database", new=AsyncMock(return_value=5)):
                count = await api.hydrate_skills()

                assert count == 5


class TestListSkills:
    """Test list_skills() and get_skill_categories()."""

    def test_list_skills_delegates_to_manager(self):
        """Test that list_skills delegates to skill manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.skill_manager, "list_skills") as mock_list:
                mock_list.return_value = [{"name": "test"}]

                result = api.list_skills()

                assert result == [{"name": "test"}]
                mock_list.assert_called_once_with(category=None)

    def test_list_skills_with_category_filter(self):
        """Test list_skills with category filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.skill_manager, "list_skills") as mock_list:
                api.list_skills(category="data_sync")

                mock_list.assert_called_once_with(category="data_sync")

    def test_get_skill_categories(self):
        """Test get_skill_categories()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            with patch.object(api.skill_manager, "get_skill_categories") as mock_get:
                mock_get.return_value = [{"name": "test", "count": 5}]

                result = api.get_skill_categories()

                assert result == [{"name": "test", "count": 5}]
                mock_get.assert_called_once()


class TestGetSkillStats:
    """Test get_skill_stats() method."""

    @pytest.mark.asyncio
    async def test_get_skill_stats(self):
        """Test getting skill statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None,
            )

            # Mock the database method
            mock_stats = {"total_skills": 10, "by_category": {"test": 5}}

            with patch.object(api.skill_manager, "get_database_stats", new=AsyncMock(return_value=mock_stats)):
                result = await api.get_skill_stats()

                assert result["total_skills"] == 10
                assert result["by_category"] == {"test": 5}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

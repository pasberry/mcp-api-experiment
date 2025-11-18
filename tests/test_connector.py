"""
Tests for MCPConnector - Code generation flow.

Tests the connector that introspects MCP servers and generates Python API wrappers.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, Mock
import asyncio

from mcp_skill_framework.connector import MCPConnector, ToolSchema


class TestToolSchema:
    """Test ToolSchema data class."""

    def test_tool_schema_initialization(self):
        """Test basic ToolSchema creation."""
        schema = ToolSchema(
            server="test_server",
            name="test_tool",
            description="Test description",
            parameters=[],
        )

        assert schema.server == "test_server"
        assert schema.name == "test_tool"
        assert schema.description == "Test description"
        assert schema.parameters == []
        assert schema.returns is None

    def test_tool_schema_with_parameters(self):
        """Test ToolSchema with parameters."""
        params = [
            {"name": "param1", "type": "string", "required": True},
            {"name": "param2", "type": "integer", "required": False},
        ]

        schema = ToolSchema(
            server="test",
            name="tool",
            description="Test",
            parameters=params,
        )

        assert len(schema.parameters) == 2
        assert schema.parameters[0]["name"] == "param1"


class TestMCPConnectorInitialization:
    """Test MCPConnector initialization."""

    def test_connector_initialization(self):
        """Test basic connector initialization."""
        connector = MCPConnector()

        assert connector.servers == {}
        assert connector.connections == {}
        assert connector.exit_stack is None
        assert connector._event_loop is None


class TestAddServer:
    """Test add_server() method."""

    def test_add_single_server(self):
        """Test adding a single server."""
        connector = MCPConnector()

        connector.add_server("test_server", "echo test")

        assert "test_server" in connector.servers
        assert connector.servers["test_server"]["command"] == "echo"
        assert connector.servers["test_server"]["args"] == ["test"]

    def test_add_server_with_multiple_args(self):
        """Test adding server with complex command."""
        connector = MCPConnector()

        connector.add_server(
            "filesystem",
            "npx -y @modelcontextprotocol/server-filesystem /tmp"
        )

        config = connector.servers["filesystem"]
        assert config["command"] == "npx"
        assert config["args"] == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]

    def test_add_server_with_env_vars(self):
        """Test adding server with environment variables."""
        connector = MCPConnector()

        env = {"API_KEY": "secret", "DEBUG": "true"}
        connector.add_server("github", "npx server-github", env=env)

        assert connector.servers["github"]["env"] == env

    def test_add_multiple_servers(self):
        """Test adding multiple servers."""
        connector = MCPConnector()

        connector.add_server("server1", "echo test1")
        connector.add_server("server2", "echo test2")
        connector.add_server("server3", "echo test3")

        assert len(connector.servers) == 3
        assert "server1" in connector.servers
        assert "server2" in connector.servers
        assert "server3" in connector.servers


class TestGetConnections:
    """Test get_connections() method."""

    def test_get_connections_empty(self):
        """Test getting connections when none exist."""
        connector = MCPConnector()

        connections = connector.get_connections()

        assert connections == {}

    def test_get_connections_after_adding(self):
        """Test getting connections after manual addition."""
        connector = MCPConnector()

        mock_session = MagicMock()
        connector.connections["test"] = mock_session

        connections = connector.get_connections()

        assert "test" in connections
        assert connections["test"] is mock_session


class TestListServers:
    """Test list_servers() method."""

    def test_list_servers_empty(self):
        """Test listing servers when none registered."""
        connector = MCPConnector()

        servers = connector.list_servers()

        assert servers == []

    def test_list_servers_not_connected(self):
        """Test listing servers without connections."""
        connector = MCPConnector()

        connector.add_server("server1", "echo test1")
        connector.add_server("server2", "echo test2")

        servers = connector.list_servers()

        assert len(servers) == 2
        assert servers[0]["name"] == "server1"
        assert servers[0]["connected"] is False
        assert servers[1]["name"] == "server2"
        assert servers[1]["connected"] is False

    def test_list_servers_with_connections(self):
        """Test listing servers with some connected."""
        connector = MCPConnector()

        connector.add_server("server1", "echo test1")
        connector.add_server("server2", "echo test2")

        # Manually add connection for server1
        connector.connections["server1"] = MagicMock()

        servers = connector.list_servers()

        assert len(servers) == 2
        assert servers[0]["connected"] is True  # server1
        assert servers[1]["connected"] is False  # server2

    def test_list_servers_sorted_by_name(self):
        """Test that servers are sorted alphabetically."""
        connector = MCPConnector()

        connector.add_server("zebra", "echo zebra")
        connector.add_server("alpha", "echo alpha")
        connector.add_server("beta", "echo beta")

        servers = connector.list_servers()

        assert servers[0]["name"] == "alpha"
        assert servers[1]["name"] == "beta"
        assert servers[2]["name"] == "zebra"


class TestDisconnectAll:
    """Test disconnect_all() method."""

    def test_disconnect_all_clears_connections(self):
        """Test that disconnect_all() clears connections."""
        connector = MCPConnector()

        # Add fake connections
        connector.connections["test1"] = MagicMock()
        connector.connections["test2"] = MagicMock()

        connector.disconnect_all()

        assert len(connector.connections) == 0
        assert connector.exit_stack is None

    def test_disconnect_all_with_exit_stack(self):
        """Test disconnect_all() with active exit stack."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            connector = MCPConnector()
            connector._event_loop = loop

            # Create mock exit stack
            mock_exit_stack = AsyncMock()
            connector.exit_stack = mock_exit_stack

            connector.disconnect_all()

            # Verify exit_stack was cleaned up
            assert connector.exit_stack is None
            assert len(connector.connections) == 0
        finally:
            loop.close()
            asyncio.set_event_loop(None)


class TestIntrospectServer:
    """Test introspect_server() method."""

    def test_introspect_server_not_connected_raises_error(self):
        """Test error when introspecting non-connected server."""
        connector = MCPConnector()

        with pytest.raises(ValueError, match="Server nonexistent not connected"):
            connector.introspect_server("nonexistent")

    @pytest.mark.asyncio
    async def test_async_introspect_server_basic(self):
        """Test async server introspection."""
        connector = MCPConnector()

        # Mock session
        mock_session = AsyncMock()

        # Mock tool list response
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter"
                }
            },
            "required": ["param1"]
        }

        mock_tools_list = MagicMock()
        mock_tools_list.tools = [mock_tool]

        mock_session.list_tools.return_value = mock_tools_list

        # Call async method
        result = await connector._async_introspect_server("test_server", mock_session)

        assert len(result) == 1
        assert result[0].name == "test_tool"
        assert result[0].description == "Test tool description"
        assert result[0].server == "test_server"
        assert len(result[0].parameters) == 1
        assert result[0].parameters[0]["name"] == "param1"
        assert result[0].parameters[0]["required"] is True

    @pytest.mark.asyncio
    async def test_async_introspect_server_multiple_tools(self):
        """Test introspecting server with multiple tools."""
        connector = MCPConnector()

        mock_session = AsyncMock()

        # Create multiple mock tools
        tools = []
        for i in range(3):
            mock_tool = MagicMock()
            mock_tool.name = f"tool_{i}"
            mock_tool.description = f"Tool {i}"
            mock_tool.inputSchema = {"type": "object", "properties": {}}
            tools.append(mock_tool)

        mock_tools_list = MagicMock()
        mock_tools_list.tools = tools

        mock_session.list_tools.return_value = mock_tools_list

        result = await connector._async_introspect_server("test", mock_session)

        assert len(result) == 3
        assert result[0].name == "tool_0"
        assert result[1].name == "tool_1"
        assert result[2].name == "tool_2"

    @pytest.mark.asyncio
    async def test_async_introspect_server_optional_parameters(self):
        """Test introspection with optional parameters."""
        connector = MCPConnector()

        mock_session = AsyncMock()

        mock_tool = MagicMock()
        mock_tool.name = "test"
        mock_tool.description = "Test"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "required_param": {"type": "string", "description": "Required"},
                "optional_param": {"type": "integer", "description": "Optional", "default": 10}
            },
            "required": ["required_param"]
        }

        mock_tools_list = MagicMock()
        mock_tools_list.tools = [mock_tool]

        mock_session.list_tools.return_value = mock_tools_list

        result = await connector._async_introspect_server("test", mock_session)

        params = result[0].parameters
        assert len(params) == 2

        # Find parameters by name
        required = [p for p in params if p["name"] == "required_param"][0]
        optional = [p for p in params if p["name"] == "optional_param"][0]

        assert required["required"] is True
        assert optional["required"] is False
        assert optional["default"] == 10


class TestListTools:
    """Test list_tools() method."""

    def test_list_tools_no_connections(self):
        """Test listing tools with no connections."""
        connector = MCPConnector()

        tools = connector.list_tools()

        assert tools == []

    def test_list_tools_filters_by_server(self):
        """Test filtering tools by specific server."""
        connector = MCPConnector()

        # Add mock connection but don't introspect
        connector.connections["server1"] = MagicMock()
        connector.connections["server2"] = MagicMock()

        # Mock introspect_server to return tools
        with patch.object(connector, 'introspect_server') as mock_introspect:
            mock_tool = MagicMock()
            mock_tool.name = "tool1"
            mock_tool.description = "Test tool"
            mock_tool.parameters = []

            mock_introspect.return_value = [mock_tool]

            # List tools for specific server
            tools = connector.list_tools(server="server1")

            # Should only call introspect for server1
            mock_introspect.assert_called_once_with("server1")

    def test_list_tools_formats_output(self):
        """Test that list_tools formats output correctly."""
        connector = MCPConnector()

        connector.connections["test_server"] = MagicMock()

        with patch.object(connector, 'introspect_server') as mock_introspect:
            mock_tool = MagicMock()
            mock_tool.name = "read_file"
            mock_tool.description = "Read a file"
            mock_tool.parameters = [{"name": "path", "type": "string"}]

            mock_introspect.return_value = [mock_tool]

            tools = connector.list_tools()

            assert len(tools) == 1
            assert tools[0]["server"] == "test_server"
            assert tools[0]["name"] == "read_file"
            assert tools[0]["function_name"] == "test_server_read_file"
            assert tools[0]["import_path"] == "servers.test_server.read_file"
            assert tools[0]["description"] == "Read a file"


class TestGenerateApis:
    """Test generate_apis() method."""

    def test_generate_apis_creates_directory_structure(self):
        """Test that generate_apis creates proper directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "servers"

            connector = MCPConnector()

            # Add mock connection
            mock_session = MagicMock()
            connector.connections["test_server"] = mock_session

            # Mock introspect_server
            with patch.object(connector, 'introspect_server') as mock_introspect:
                mock_tool = ToolSchema(
                    server="test_server",
                    name="test_tool",
                    description="Test",
                    parameters=[]
                )

                mock_introspect.return_value = [mock_tool]

                connector.generate_apis(output_dir)

                # Verify directory structure
                assert output_dir.exists()
                assert (output_dir / "test_server").exists()
                assert (output_dir / "test_server" / "test_tool").exists()
                assert (output_dir / "test_server" / "test_tool" / "main.py").exists()
                assert (output_dir / "test_server" / "test_tool" / "README.md").exists()
                assert (output_dir / "test_server" / "test_tool" / "__init__.py").exists()

    def test_generate_apis_multiple_tools(self):
        """Test generating APIs for multiple tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "servers"

            connector = MCPConnector()
            connector.connections["test_server"] = MagicMock()

            with patch.object(connector, 'introspect_server') as mock_introspect:
                tools = [
                    ToolSchema("test_server", "tool1", "Tool 1", []),
                    ToolSchema("test_server", "tool2", "Tool 2", []),
                    ToolSchema("test_server", "tool3", "Tool 3", []),
                ]

                mock_introspect.return_value = tools

                connector.generate_apis(output_dir)

                # Verify all tools were generated
                assert (output_dir / "test_server" / "tool1" / "main.py").exists()
                assert (output_dir / "test_server" / "tool2" / "main.py").exists()
                assert (output_dir / "test_server" / "tool3" / "main.py").exists()

    def test_generate_apis_multiple_servers(self):
        """Test generating APIs for multiple servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "servers"

            connector = MCPConnector()
            connector.connections["server1"] = MagicMock()
            connector.connections["server2"] = MagicMock()

            def mock_introspect(server_name):
                return [ToolSchema(server_name, "tool", f"Tool for {server_name}", [])]

            with patch.object(connector, 'introspect_server', side_effect=mock_introspect):
                connector.generate_apis(output_dir)

                # Verify both servers were generated
                assert (output_dir / "server1" / "tool" / "main.py").exists()
                assert (output_dir / "server2" / "tool" / "main.py").exists()


class TestGenerateApiFiles:
    """Test _generate_api_files() helper method."""

    def test_generate_api_files_creates_all_files(self):
        """Test that _generate_api_files creates all required files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server_dir = Path(tmpdir) / "test_server"
            server_dir.mkdir()

            connector = MCPConnector()

            tool = ToolSchema(
                server="test_server",
                name="test_tool",
                description="Test tool description",
                parameters=[
                    {"name": "param1", "type": "string", "required": True, "description": "Param 1"}
                ]
            )

            connector._generate_api_files(tool, server_dir)

            tool_dir = server_dir / "test_tool"

            # Check all files exist
            assert (tool_dir / "main.py").exists()
            assert (tool_dir / "README.md").exists()
            assert (tool_dir / "__init__.py").exists()

    def test_generate_api_files_content(self):
        """Test that generated files have correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server_dir = Path(tmpdir) / "test_server"
            server_dir.mkdir()

            connector = MCPConnector()

            tool = ToolSchema(
                server="test_server",
                name="read_file",
                description="Read a file",
                parameters=[
                    {"name": "path", "type": "string", "required": True, "description": "File path"}
                ]
            )

            connector._generate_api_files(tool, server_dir)

            tool_dir = server_dir / "test_tool"

            # Read generated main.py
            main_py = (server_dir / "read_file" / "main.py").read_text()

            # Verify function naming pattern
            assert "def test_server_read_file(" in main_py
            assert "from mcp_skill_framework.runtime import mcp_call" in main_py
            assert 'server="test_server"' in main_py
            assert 'tool="read_file"' in main_py

            # Read generated README
            readme = (server_dir / "read_file" / "README.md").read_text()

            assert "# read_file" in readme
            assert "Read a file" in readme
            assert "**Domain:** test_server" in readme


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

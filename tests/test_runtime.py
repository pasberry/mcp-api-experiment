"""
Tests for MCP Runtime - Core execution path.

Tests the critical mcp_call() function and MCPRuntime class that handles
all MCP tool execution from generated APIs.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any, Dict

from src.runtime import mcp_call, MCPRuntime, _runtime_instance


class TestMCPCallGlobalFunction:
    """Test the mcp_call() global function."""

    def test_mcp_call_without_runtime_raises_error(self):
        """Test that mcp_call() raises error when runtime not initialized."""
        # Clear global instance
        import src.runtime as runtime_module

        runtime_module._runtime_instance = None

        with pytest.raises(RuntimeError, match="MCP Runtime not initialized"):
            mcp_call("test_server", "test_tool", {})

    def test_mcp_call_routes_to_runtime(self):
        """Test that mcp_call() routes to runtime instance."""
        # Create mock runtime
        mock_runtime = MagicMock()
        mock_runtime.call.return_value = "test_result"

        # Set as global instance
        import src.runtime as runtime_module

        runtime_module._runtime_instance = mock_runtime

        # Call mcp_call
        result = mcp_call("test_server", "test_tool", {"param": "value"})

        # Verify routing
        mock_runtime.call.assert_called_once_with("test_server", "test_tool", {"param": "value"})
        assert result == "test_result"

        # Cleanup
        runtime_module._runtime_instance = None


class TestMCPRuntimeInitialization:
    """Test MCPRuntime initialization."""

    def test_runtime_initialization(self):
        """Test that runtime initializes correctly."""
        runtime = MCPRuntime(telemetry=None)

        assert runtime.servers == {}
        assert runtime.telemetry is None
        assert runtime._event_loop is None

    def test_runtime_sets_global_instance(self):
        """Test that runtime sets itself as global instance."""
        import src.runtime as runtime_module

        # Clear global
        runtime_module._runtime_instance = None

        # Create runtime
        runtime = MCPRuntime()

        # Verify global instance is set
        assert runtime_module._runtime_instance is runtime

        # Cleanup
        runtime_module._runtime_instance = None

    def test_runtime_with_telemetry(self):
        """Test runtime initialization with telemetry."""
        mock_telemetry = MagicMock()
        runtime = MCPRuntime(telemetry=mock_telemetry)

        assert runtime.telemetry is mock_telemetry


class TestRegisterServers:
    """Test server registration."""

    def test_register_servers_stores_connections(self):
        """Test that register_servers stores connections."""
        runtime = MCPRuntime()

        mock_session1 = MagicMock()
        mock_session2 = MagicMock()

        connections = {"server1": mock_session1, "server2": mock_session2}

        runtime.register_servers(connections)

        assert runtime.servers == connections
        assert "server1" in runtime.servers
        assert "server2" in runtime.servers

    def test_register_servers_creates_event_loop(self):
        """Test that register_servers creates event loop."""
        runtime = MCPRuntime()

        connections = {"test_server": MagicMock()}
        runtime.register_servers(connections)

        assert runtime._event_loop is not None
        assert isinstance(runtime._event_loop, asyncio.AbstractEventLoop)


class TestMCPRuntimeCall:
    """Test the runtime.call() method."""

    def test_call_with_unregistered_server_raises_error(self):
        """Test that calling unregistered server raises ValueError."""
        runtime = MCPRuntime()
        runtime.register_servers({})

        with pytest.raises(ValueError, match="Server 'nonexistent' not registered"):
            runtime.call("nonexistent", "test_tool", {})

    def test_call_without_event_loop_raises_error(self):
        """Test that calling without event loop raises RuntimeError."""
        runtime = MCPRuntime()
        runtime.servers = {"test_server": MagicMock()}
        runtime._event_loop = None

        with pytest.raises(RuntimeError, match="Event loop not initialized"):
            runtime.call("test_server", "test_tool", {})

    def test_call_executes_async_call(self):
        """Test that call() executes async call correctly."""
        # Create new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            runtime = MCPRuntime()

            # Mock session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.content = [MagicMock(text="test_response")]

            # Make call_tool return a coroutine
            async def mock_call_tool(tool, params):
                return mock_result

            mock_session.call_tool = mock_call_tool

            # Register server
            runtime.register_servers({"test_server": mock_session})

            # Execute call
            result = runtime.call("test_server", "test_tool", {"param": "value"})

            # Verify result
            assert result == "test_response"
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_call_logs_telemetry_on_success(self):
        """Test that successful calls log telemetry."""
        # Create new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            mock_telemetry = MagicMock()
            runtime = MCPRuntime(telemetry=mock_telemetry)

            # Mock session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.content = [MagicMock(text="success")]

            async def mock_call_tool(tool, params):
                return mock_result

            mock_session.call_tool = mock_call_tool

            runtime.register_servers({"test_server": mock_session})

            # Execute call
            runtime.call("test_server", "test_tool", {"param": "value"})

            # Verify telemetry was called
            mock_telemetry.log_mcp_call.assert_called_once()
            call_args = mock_telemetry.log_mcp_call.call_args[1]

            assert call_args["server"] == "test_server"
            assert call_args["tool"] == "test_tool"
            assert call_args["params"] == {"param": "value"}
            assert call_args["success"] is True
            assert call_args["result"] == "success"
            assert call_args["error"] is None
            assert call_args["duration_ms"] > 0
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_call_logs_telemetry_on_error(self):
        """Test that failed calls log telemetry with error."""
        # Create new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            mock_telemetry = MagicMock()
            runtime = MCPRuntime(telemetry=mock_telemetry)

            # Mock session that raises error
            mock_session = MagicMock()

            async def mock_call_tool(tool, params):
                raise Exception("Test error")

            mock_session.call_tool = mock_call_tool

            runtime.register_servers({"test_server": mock_session})

            # Execute call and expect error
            with pytest.raises(Exception, match="Test error"):
                runtime.call("test_server", "test_tool", {})

            # Verify telemetry was called with error
            mock_telemetry.log_mcp_call.assert_called_once()
            call_args = mock_telemetry.log_mcp_call.call_args[1]

            assert call_args["success"] is False
            assert call_args["error"] is not None
            assert "Test error" in str(call_args["error"])
        finally:
            loop.close()
            asyncio.set_event_loop(None)


class TestAsyncCallResultExtraction:
    """Test result extraction from MCP responses."""

    @pytest.mark.asyncio
    async def test_async_call_extracts_text_from_content(self):
        """Test extraction of text from content array."""
        runtime = MCPRuntime()

        # Mock session with text content
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="extracted_text")]

        async def mock_call_tool(tool, params):
            return mock_result

        mock_session.call_tool = mock_call_tool

        runtime.servers = {"test_server": mock_session}

        # Execute async call
        result = await runtime._async_call("test_server", "test_tool", {})

        assert result == "extracted_text"

    @pytest.mark.asyncio
    async def test_async_call_handles_empty_content(self):
        """Test handling of empty content array."""
        runtime = MCPRuntime()

        # Mock session with empty content
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.content = []

        async def mock_call_tool(tool, params):
            return mock_result

        mock_session.call_tool = mock_call_tool

        runtime.servers = {"test_server": mock_session}

        # Execute async call
        result = await runtime._async_call("test_server", "test_tool", {})

        # Empty list is falsy, so code returns raw result
        # (because of `if hasattr(result, 'content') and result.content:`)
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_async_call_returns_raw_result_without_content(self):
        """Test return of raw result when no content field."""
        runtime = MCPRuntime()

        # Mock session with no content field
        mock_session = MagicMock()
        mock_result = {"data": "raw_result"}

        async def mock_call_tool(tool, params):
            return mock_result

        mock_session.call_tool = mock_call_tool

        runtime.servers = {"test_server": mock_session}

        # Execute async call
        result = await runtime._async_call("test_server", "test_tool", {})

        assert result == {"data": "raw_result"}

    @pytest.mark.asyncio
    async def test_async_call_handles_non_text_content(self):
        """Test handling of content without text attribute."""
        runtime = MCPRuntime()

        # Mock session with content but no text
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_content_item = {"type": "image", "data": "base64data"}
        mock_result.content = [mock_content_item]

        async def mock_call_tool(tool, params):
            return mock_result

        mock_session.call_tool = mock_call_tool

        runtime.servers = {"test_server": mock_session}

        # Execute async call
        result = await runtime._async_call("test_server", "test_tool", {})

        # Should return first content item
        assert result == mock_content_item


class TestRuntimeClear:
    """Test runtime cleanup."""

    def test_clear_removes_servers(self):
        """Test that clear() removes registered servers."""
        runtime = MCPRuntime()
        runtime.register_servers({"server1": MagicMock()})

        assert len(runtime.servers) == 1

        runtime.clear()

        assert len(runtime.servers) == 0
        assert runtime._event_loop is None


class TestConcurrentCalls:
    """Test concurrent MCP calls."""

    def test_multiple_sequential_calls(self):
        """Test multiple sequential calls to different tools."""
        # Create new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            runtime = MCPRuntime()

            # Mock session
            mock_session = MagicMock()
            call_count = 0

            async def mock_call_tool(tool, params):
                nonlocal call_count
                call_count += 1
                result = MagicMock()
                result.content = [MagicMock(text=f"response_{call_count}")]
                return result

            mock_session.call_tool = mock_call_tool

            runtime.register_servers({"test_server": mock_session})

            # Make multiple calls
            result1 = runtime.call("test_server", "tool1", {})
            result2 = runtime.call("test_server", "tool2", {})
            result3 = runtime.call("test_server", "tool3", {})

            assert result1 == "response_1"
            assert result2 == "response_2"
            assert result3 == "response_3"
            assert call_count == 3
        finally:
            loop.close()
            asyncio.set_event_loop(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

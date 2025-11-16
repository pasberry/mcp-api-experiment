"""
MCP Runtime - Executes MCP calls from generated APIs.
"""

from typing import Dict, Any, Optional
import logging
import asyncio

from mcp import ClientSession

logger = logging.getLogger(__name__)

# Global runtime instance
_runtime_instance: Optional["MCPRuntime"] = None


def mcp_call(server: str, tool: str, params: Dict[str, Any]) -> Any:
    """
    Execute an MCP tool call.

    This function is called by generated APIs and injected into
    the agent's execution environment.

    Args:
        server: Server name (e.g., 'google-drive')
        tool: Tool name (e.g., 'list_files')
        params: Tool parameters

    Returns:
        Tool execution result

    Raises:
        RuntimeError: If runtime not initialized
        Exception: If MCP call fails
    """
    if _runtime_instance is None:
        raise RuntimeError("MCP Runtime not initialized")

    return _runtime_instance.call(server, tool, params)


class MCPRuntime:
    """
    Runtime that routes Python function calls to MCP servers.

    This component:
    1. Maintains connections to MCP servers
    2. Routes mcp_call() to the correct server
    3. Handles MCP protocol details
    """

    def __init__(self):
        self.servers: Dict[str, ClientSession] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._setup_global_instance()

    def _setup_global_instance(self) -> None:
        """Set this as the global runtime instance."""
        global _runtime_instance
        _runtime_instance = self

    def register_servers(self, connections: Dict[str, ClientSession]) -> None:
        """
        Register MCP server connections.

        Args:
            connections: Dict mapping server names to ClientSession objects
        """
        self.servers = connections

        # Get or create event loop
        try:
            self._event_loop = asyncio.get_event_loop()
        except RuntimeError:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

        logger.info(f"Registered {len(connections)} MCP servers")

    def call(self, server: str, tool: str, params: Dict[str, Any]) -> Any:
        """
        Execute an MCP tool call.

        Args:
            server: Server name
            tool: Tool name
            params: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ValueError: If server not registered
            Exception: If MCP call fails
        """
        logger.debug(f"MCP call: {server}.{tool}({params})")

        if server not in self.servers:
            raise ValueError(f"Server '{server}' not registered in runtime")

        if not self._event_loop:
            raise RuntimeError("Event loop not initialized")

        # Execute async call
        result = self._event_loop.run_until_complete(
            self._async_call(server, tool, params)
        )

        return result

    async def _async_call(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Async implementation of MCP call.

        Args:
            server: Server name
            tool: Tool name
            params: Tool parameters

        Returns:
            Tool execution result
        """
        session = self.servers[server]

        try:
            # Call tool via MCP
            result = await session.call_tool(tool, params)

            # Extract content from result
            if hasattr(result, 'content') and result.content:
                # If result has content array, extract text
                if isinstance(result.content, list) and len(result.content) > 0:
                    first_content = result.content[0]
                    if hasattr(first_content, 'text'):
                        return first_content.text
                    return first_content
                return result.content

            # Return raw result if no content field
            return result

        except Exception as e:
            logger.error(f"MCP call failed: {server}.{tool} - {e}")
            raise

    def clear(self) -> None:
        """Clear registered servers."""
        self.servers.clear()
        self._event_loop = None
        logger.info("Cleared MCP runtime")

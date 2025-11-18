"""Mock MCP ClientSession for testing."""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


class MockClientSession:
    """Mock MCP ClientSession for testing."""

    def __init__(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
        call_responses: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize mock session.

        Args:
            tools: List of tool schemas to return from list_tools()
            call_responses: Dict mapping tool names to responses
        """
        self.tools = tools or []
        self.call_responses = call_responses or {}
        self.calls_made: List[Dict[str, Any]] = []

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    async def initialize(self):
        """Initialize the session."""
        pass

    async def list_tools(self) -> Dict[str, Any]:
        """Mock list_tools call."""
        return {"tools": self.tools}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock tool call.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Mock response
        """
        # Record the call
        self.calls_made.append({"tool": tool_name, "arguments": arguments})

        # Return configured response or default
        if tool_name in self.call_responses:
            response = self.call_responses[tool_name]
            if isinstance(response, Exception):
                raise response
            return response

        # Default success response
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Mock response for {tool_name}",
                }
            ]
        }


def create_mock_session(
    tools: Optional[List[Dict[str, Any]]] = None,
    responses: Optional[Dict[str, Any]] = None,
) -> MockClientSession:
    """
    Factory function to create mock session.

    Args:
        tools: Tool schemas
        responses: Tool call responses

    Returns:
        MockClientSession instance
    """
    return MockClientSession(tools=tools, call_responses=responses)


def create_mock_tool_schema(
    name: str,
    description: str = "Test tool",
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a mock tool schema.

    Args:
        name: Tool name
        description: Tool description
        parameters: JSON schema for parameters

    Returns:
        Tool schema dict
    """
    if parameters is None:
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
        }

    return {
        "name": name,
        "description": description,
        "inputSchema": parameters,
    }

"""
MCP Connector - Connects to MCP servers and generates Python APIs.
"""

from typing import Dict, Optional, Any, List
from pathlib import Path
import logging
import asyncio
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class ToolSchema:
    """Represents an MCP tool schema."""

    def __init__(
        self,
        server: str,
        name: str,
        description: str,
        parameters: List[Dict[str, Any]],
        returns: Optional[Dict[str, Any]] = None,
    ):
        self.server = server
        self.name = name
        self.description = description
        self.parameters = parameters
        self.returns = returns


class MCPConnector:
    """
    Connects to MCP servers and generates Python API wrappers.

    This component:
    1. Connects to MCP servers via stdio/HTTP
    2. Introspects available tools
    3. Generates semantic directory structure with Python APIs
    """

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.connections: Dict[str, ClientSession] = {}
        self.exit_stack: Optional[AsyncExitStack] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    def add_server(self, name: str, command: str, env: Optional[Dict[str, str]] = None) -> None:
        """
        Register an MCP server.

        Args:
            name: Server identifier
            command: Command to start the server (e.g., 'npx server' or 'python server.py')
            env: Optional environment variables
        """
        # Parse command into command and args
        parts = command.split()
        self.servers[name] = {
            "command": parts[0],
            "args": parts[1:] if len(parts) > 1 else [],
            "env": env or {},
        }
        logger.info(f"Registered MCP server: {name}")

    def connect_all(self) -> None:
        """
        Connect to all registered MCP servers.
        """
        logger.info("Connecting to MCP servers...")

        # Get or create event loop
        try:
            self._event_loop = asyncio.get_event_loop()
        except RuntimeError:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

        # Run async connection
        self._event_loop.run_until_complete(self._async_connect_all())

    async def _async_connect_all(self) -> None:
        """Async implementation of connect_all."""
        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()

        for server_name, server_config in self.servers.items():
            try:
                logger.info(f"Connecting to {server_name}...")

                # Create server parameters
                server_params = StdioServerParameters(
                    command=server_config["command"],
                    args=server_config["args"],
                    env=server_config["env"] if server_config["env"] else None,
                )

                # Create stdio client
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                read_stream, write_stream = stdio_transport

                # Create session
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                # Initialize session
                await session.initialize()

                self.connections[server_name] = session
                logger.info(f"Connected to {server_name}")

            except Exception as e:
                logger.error(f"Failed to connect to {server_name}: {e}")
                raise

    def disconnect_all(self) -> None:
        """
        Disconnect from all MCP servers.
        """
        logger.info("Disconnecting from MCP servers...")

        if self.exit_stack and self._event_loop:
            self._event_loop.run_until_complete(
                self.exit_stack.__aexit__(None, None, None)
            )

        self.connections.clear()
        self.exit_stack = None

    def get_connections(self) -> Dict[str, ClientSession]:
        """
        Get active MCP connections.

        Returns:
            Dict mapping server names to ClientSession objects
        """
        return self.connections

    def introspect_server(self, server_name: str) -> List[ToolSchema]:
        """
        Introspect an MCP server to get available tools.

        Args:
            server_name: Name of the server

        Returns:
            List of tool schemas
        """
        if server_name not in self.connections:
            raise ValueError(f"Server {server_name} not connected")

        session = self.connections[server_name]

        # Run async introspection
        return self._event_loop.run_until_complete(
            self._async_introspect_server(server_name, session)
        )

    async def _async_introspect_server(
        self,
        server_name: str,
        session: ClientSession
    ) -> List[ToolSchema]:
        """Async implementation of introspect_server."""
        logger.info(f"Introspecting {server_name}...")

        # List available tools
        tools_list = await session.list_tools()

        tool_schemas = []
        for tool in tools_list.tools:
            # Parse parameter schema
            parameters = []
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                if 'properties' in schema:
                    for param_name, param_def in schema['properties'].items():
                        parameters.append({
                            'name': param_name,
                            'type': param_def.get('type', 'any'),
                            'description': param_def.get('description', ''),
                            'required': param_name in schema.get('required', []),
                            'default': param_def.get('default'),
                        })

            tool_schema = ToolSchema(
                server=server_name,
                name=tool.name,
                description=tool.description or "",
                parameters=parameters,
                returns=None,  # MCP doesn't provide return type schema
            )
            tool_schemas.append(tool_schema)

        logger.info(f"Found {len(tool_schemas)} tools in {server_name}")
        return tool_schemas

    def generate_apis(self, output_dir: Path) -> None:
        """
        Generate Python APIs for all connected servers.

        Creates:
        - servers/{server_name}/{tool_name}/main.py
        - servers/{server_name}/{tool_name}/README.md
        - servers/{server_name}/{tool_name}/__init__.py

        Args:
            output_dir: Directory to write generated APIs
        """
        from .templates import generate_main_py, generate_readme_md, generate_init_py

        logger.info(f"Generating APIs to {output_dir}")

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate APIs for each server
        for server_name in self.connections.keys():
            logger.info(f"Generating APIs for {server_name}...")

            # Introspect server
            tool_schemas = self.introspect_server(server_name)

            # Create server directory
            server_dir = output_dir / server_name
            server_dir.mkdir(parents=True, exist_ok=True)

            # Generate API for each tool
            for tool in tool_schemas:
                self._generate_api_files(tool, server_dir)

            logger.info(f"Generated {len(tool_schemas)} APIs for {server_name}")

        logger.info("API generation complete")

    def _generate_api_files(
        self,
        tool: ToolSchema,
        server_dir: Path,
    ) -> None:
        """
        Generate all files for a single tool.

        Args:
            tool: Tool schema
            server_dir: Server directory path
        """
        from .templates import generate_main_py, generate_readme_md, generate_init_py

        # Create tool directory: servers/{server_name}/{tool_name}/
        tool_dir = server_dir / tool.name
        tool_dir.mkdir(parents=True, exist_ok=True)

        # Generate main.py
        main_py_path = tool_dir / "main.py"
        main_py_content = generate_main_py(tool)
        main_py_path.write_text(main_py_content)
        logger.debug(f"Generated {main_py_path}")

        # Generate README.md
        readme_path = tool_dir / "README.md"
        readme_content = generate_readme_md(tool)
        readme_path.write_text(readme_content)
        logger.debug(f"Generated {readme_path}")

        # Generate __init__.py
        init_path = tool_dir / "__init__.py"
        init_content = generate_init_py(tool.description)
        init_path.write_text(init_content)
        logger.debug(f"Generated {init_path}")

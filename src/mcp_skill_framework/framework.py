"""
Main MCPApi class that orchestrates all components.

This is a code generation and skill persistence tool, not an execution environment.
The agent runs in its own environment and uses the generated libraries.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import asyncio

from .connector import MCPConnector
from .runtime import MCPRuntime
from .skill_manager import SkillManager
from .telemetry import TelemetryLogger


class MCPApi:
    """
    MCP Code Generation and Skill Persistence Tool.

    This tool:
    1. Generates Python libraries from MCP servers (servers/ package)
    2. Hydrates agent skills from database on startup (skills/ package)
    3. Persists new skills created by agents (filesystem + database)

    The agent runs code in its own environment, not here.
    """

    def __init__(
        self,
        agent_name: str,
        servers_dir: str = "servers",
        skills_dir: str = "skills",
        skills_db: str = "skills.db",
        telemetry_db: Optional[str] = ".mcp_telemetry/telemetry.db",
    ):
        """
        Initialize the API.

        Args:
            agent_name: Agent identifier for skill persistence
            servers_dir: Directory where generated MCP libraries are stored
            skills_dir: Directory where agent skills are stored
            skills_db: Path to skills database
            telemetry_db: Path to telemetry database (None to disable)
        """
        self.agent_name = agent_name
        self.servers_dir = Path(servers_dir)
        self.skills_dir = Path(skills_dir)
        self.skills_db_path = Path(skills_db)

        # Create directories if they don't exist
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # Initialize telemetry
        self.telemetry = None
        if telemetry_db:
            telemetry_path = Path(telemetry_db)
            self.telemetry = TelemetryLogger(telemetry_path)

        # Initialize components
        self.connector = MCPConnector()
        self.runtime = MCPRuntime(telemetry=self.telemetry)
        self.skill_manager = SkillManager(
            skills_dir=self.skills_dir,
            agent_name=self.agent_name,
            db_path=self.skills_db_path,
            telemetry=self.telemetry,
        )

        self._started = False

    def add_mcp_server(
        self,
        name: str,
        command: str,
        env: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Register an MCP server for code generation.

        Args:
            name: Server identifier (e.g., 'google-drive')
            command: Command to start MCP server (e.g., 'npx @google/drive-mcp-server')
            env: Optional environment variables for the server
        """
        self.connector.add_server(name, command, env)

    def generate_libraries(self) -> None:
        """
        Generate Python libraries from all registered MCP servers.

        Creates importable packages in servers/ directory:
        - servers/{server_name}/{tool_name}/main.py
        - servers/{server_name}/{tool_name}/README.md
        - servers/{server_name}/{tool_name}/__init__.py

        This is a one-time codegen step. Commit the generated code to git.
        """
        # Temporarily connect to introspect
        self.connector.connect_all()
        self.connector.generate_apis(output_dir=self.servers_dir)
        self.connector.disconnect_all()

    async def hydrate_skills(self) -> int:
        """
        Hydrate agent skills from database to filesystem.

        Call this during agent startup to restore previously learned skills.
        Database is the source of truth - clears filesystem and rebuilds.

        Returns:
            Number of skills hydrated

        Example:
            await api.hydrate_skills()
        """
        return await self.skill_manager.hydrate_from_database()

    def start(self) -> None:
        """
        Start the runtime (connect to MCP servers).

        The runtime is needed for the generated server libraries to work.
        Call this when your agent starts up, after hydrating skills.
        """
        if self._started:
            return

        self.connector.connect_all()
        self.runtime.register_servers(self.connector.get_connections())
        self._started = True

    def stop(self) -> None:
        """
        Stop the runtime (disconnect from MCP servers).

        Call this when your agent shuts down.
        """
        if not self._started:
            return

        self.connector.disconnect_all()
        self.runtime.clear()
        self._started = False

    def save_skill(
        self,
        code: str,
        name: str,
        category: str = "general",
        tags: Optional[list] = None,
        persist_to_db: bool = True
    ) -> None:
        """
        Save agent code as a reusable skill.

        Immediately writes to filesystem (so agent can import it) and
        optionally persists to database asynchronously (for future hydration).

        Args:
            code: Python code to save
            name: Skill name
            category: Skill category
            tags: Optional tags for discovery
            persist_to_db: Whether to persist to database (default True)

        Example:
            # Agent writes working code
            def backup_files(folder_id):
                from servers.google_drive.list_files import list_files
                files = list_files(folder_id)
                return files

            # Save as skill
            import inspect
            api.save_skill(
                code=inspect.getsource(backup_files),
                name="backup_files",
                category="data_sync"
            )

            # Later, agent can import:
            # from skills.data_sync.backup_files import backup_files
        """
        self.skill_manager.save_skill(
            code=code,
            name=name,
            category=category,
            tags=tags,
            persist_to_db=persist_to_db
        )

    def list_skills(self, category: Optional[str] = None) -> list:
        """
        List available skills from filesystem.

        Args:
            category: Optional category filter

        Returns:
            List of skill metadata dicts
        """
        return self.skill_manager.list_skills(category=category)

    def get_skill_categories(self) -> list:
        """
        Get list of skill categories with counts.

        Returns:
            List of dicts with category name and skill count

        Example:
            categories = api.get_skill_categories()
            # [{"name": "file_operations", "count": 5}, ...]
        """
        return self.skill_manager.get_skill_categories()

    def list_servers(self) -> list:
        """
        List all registered MCP servers with connection status.

        Returns:
            List of server info dicts

        Example:
            servers = api.list_servers()
            # [{"name": "filesystem", "connected": True}, ...]
        """
        return self.connector.list_servers()

    def list_mcp_tools(self, server: Optional[str] = None) -> list:
        """
        List available MCP tools from connected servers.

        Args:
            server: Optional server name to filter tools

        Returns:
            List of tool info dicts with import paths

        Example:
            # List all tools
            tools = api.list_mcp_tools()

            # List tools from specific server
            tools = api.list_mcp_tools(server="filesystem")

            # Each tool dict contains:
            # {
            #   "server": "filesystem",
            #   "name": "read_file",
            #   "function_name": "filesystem_read_file",
            #   "import_path": "servers.filesystem.read_file",
            #   "description": "Read file contents"
            # }
        """
        return self.connector.list_tools(server=server)

    async def get_skill_stats(self) -> Dict[str, Any]:
        """
        Get statistics about agent's skills in database.

        Returns:
            Stats dictionary with counts by category

        Example:
            stats = await api.get_skill_stats()
            print(f"Total skills: {stats['total_skills']}")
            print(f"By category: {stats['by_category']}")
        """
        return await self.skill_manager.get_database_stats()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated telemetry metrics.

        Returns:
            Dict with telemetry data or disabled message
        """
        if not self.telemetry:
            return {
                "telemetry_enabled": False,
                "message": "Telemetry is disabled"
            }

        return {
            "telemetry_enabled": True,
            "tool_metrics": self.telemetry.get_tool_metrics(),
            "health_snapshot": self.telemetry.get_health_snapshot(),
        }

    def __enter__(self):
        """Context manager support - starts runtime."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support - stops runtime and closes telemetry."""
        self.stop()
        if self.telemetry:
            self.telemetry.close()

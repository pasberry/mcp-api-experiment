"""
Main MCPApi class that orchestrates all components.
"""

from typing import Optional, Dict, Any
from pathlib import Path

from .connector import MCPConnector
from .runtime import MCPRuntime
from .executor import CodeExecutor
from .skill_manager import SkillManager
from .checkpoint_manager import CheckpointManager


class MCPApi:
    """
    Main entry point for the MCP Skill Framework.

    Orchestrates MCP connection, API generation, code execution,
    skill persistence, and checkpoint management.
    """

    def __init__(
        self,
        servers_dir: str = "servers",
        skills_dir: str = "skills",
        tasks_dir: str = "tasks",
        use_docker: bool = True,
    ):
        """
        Initialize the API.

        Args:
            servers_dir: Directory where generated APIs are stored
            skills_dir: Directory where agent skills accumulate
            tasks_dir: Directory where task checkpoints are saved
            use_docker: Whether to use Docker for code execution (falls back to subprocess if unavailable)
        """
        self.servers_dir = Path(servers_dir)
        self.skills_dir = Path(skills_dir)
        self.tasks_dir = Path(tasks_dir)

        # Create directories if they don't exist
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.connector = MCPConnector()
        self.runtime = MCPRuntime()
        self.executor = CodeExecutor(
            servers_dir=self.servers_dir,
            skills_dir=self.skills_dir,
            tasks_dir=self.tasks_dir,
            runtime=self.runtime,
            use_docker=use_docker,
        )
        self.skill_manager = SkillManager(skills_dir=self.skills_dir)
        self.checkpoint_manager = CheckpointManager(tasks_dir=self.tasks_dir)

        self._started = False

    def add_mcp_server(self, name: str, command: str, env: Optional[Dict[str, str]] = None) -> None:
        """
        Register an MCP server.

        Args:
            name: Server identifier (e.g., 'google-drive')
            command: Command to start MCP server (e.g., 'npx @google/drive-mcp-server')
            env: Optional environment variables for the server
        """
        self.connector.add_server(name, command, env)

    def generate_apis(self) -> None:
        """
        Generate Python APIs from all registered MCP servers.

        Creates semantic directory structure:
        servers/{server_name}/{tool_name}/main.py
        servers/{server_name}/{tool_name}/README.md
        """
        if not self._started:
            # Temporarily connect to introspect
            self.connector.connect_all()
            self.connector.generate_apis(output_dir=self.servers_dir)
            self.connector.disconnect_all()
        else:
            # Already connected
            self.connector.generate_apis(output_dir=self.servers_dir)

    def start(self) -> None:
        """
        Start the framework runtime.

        Connects to all MCP servers and prepares for code execution.
        """
        if self._started:
            return

        self.connector.connect_all()
        self.runtime.register_servers(self.connector.get_connections())
        self._started = True

    def stop(self) -> None:
        """
        Stop the framework runtime.

        Disconnects from MCP servers and cleans up resources.
        """
        if not self._started:
            return

        self.connector.disconnect_all()
        self.runtime.clear()
        self._started = False

    def execute(self, code: str, save_as_skill: Optional[str] = None, category: str = "general") -> Any:
        """
        Execute agent code in sandboxed environment.

        Args:
            code: Python code to execute
            save_as_skill: If provided, save code as a skill with this name
            category: Category for the skill (if saving)

        Returns:
            Execution result
        """
        if not self._started:
            raise RuntimeError("MCPApi not started. Call start() first.")

        result = self.executor.execute(code)

        if save_as_skill:
            self.skill_manager.save_skill(
                code=code,
                name=save_as_skill,
                category=category,
            )

        return result

    def save_skill(self, code: str, name: str, category: str = "general") -> None:
        """
        Save code as a reusable skill.

        Args:
            code: Python code to save
            name: Skill name
            category: Skill category
        """
        self.skill_manager.save_skill(code=code, name=name, category=category)

    def list_skills(self, category: Optional[str] = None) -> list:
        """
        List available skills.

        Args:
            category: Optional category filter

        Returns:
            List of skill metadata
        """
        return self.skill_manager.list_skills(category=category)

    def create_checkpoint(self, task_id: str, state: Dict[str, Any], code: str) -> None:
        """
        Create a checkpoint for a task.

        Args:
            task_id: Unique task identifier
            state: State dict to save
            code: Resume code
        """
        self.checkpoint_manager.create_checkpoint(
            task_id=task_id,
            state=state,
            code=code,
        )

    def resume_checkpoint(self, task_id: str) -> Any:
        """
        Resume from a checkpoint.

        Args:
            task_id: Task identifier

        Returns:
            Result of resume execution
        """
        return self.checkpoint_manager.resume_checkpoint(task_id)

    def __enter__(self):
        """Context manager support."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.stop()

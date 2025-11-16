"""
Code Executor - Runs agent code in sandboxed environment.
"""

from typing import Any, Optional, Dict
from pathlib import Path
import logging
import subprocess
import sys
import tempfile
import json

logger = logging.getLogger(__name__)


class CodeExecutor:
    """
    Executes agent code in isolated environment.

    This component:
    1. Prepares execution environment with access to servers/ and skills/
    2. Executes code safely in subprocess
    3. Returns results to agent

    Note: Currently uses subprocess isolation. Full Docker support
    can be added in future versions.
    """

    def __init__(
        self,
        servers_dir: Path,
        skills_dir: Path,
        tasks_dir: Path,
        runtime: Any,
    ):
        """
        Initialize code executor.

        Args:
            servers_dir: Path to generated server APIs
            skills_dir: Path to agent skills
            tasks_dir: Path to task checkpoints
            runtime: MCPRuntime instance
        """
        self.servers_dir = servers_dir.resolve()
        self.skills_dir = skills_dir.resolve()
        self.tasks_dir = tasks_dir.resolve()
        self.runtime = runtime

    def execute(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute code in sandboxed subprocess.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: 'success', 'result', 'stdout', 'stderr'
        """
        logger.info("Executing code in sandbox...")

        try:
            # Create wrapper script that sets up environment
            wrapper_code = self._create_wrapper(code)

            # Write to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(wrapper_code)
                temp_file = f.name

            try:
                # Execute in subprocess
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(self.servers_dir.parent),  # Run from project root
                )

                # Parse result
                if result.returncode == 0:
                    return {
                        'success': True,
                        'result': result.stdout,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                    }
                else:
                    return {
                        'success': False,
                        'result': None,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'error': f"Exit code: {result.returncode}",
                    }

            finally:
                # Clean up temp file
                Path(temp_file).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logger.error(f"Code execution timed out after {timeout}s")
            return {
                'success': False,
                'result': None,
                'error': f"Execution timed out after {timeout}s",
            }
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
            }

    def _create_wrapper(self, code: str) -> str:
        """
        Create wrapper script that sets up execution environment.

        Args:
            code: User code to execute

        Returns:
            Wrapper code
        """
        # Build PYTHONPATH additions
        python_paths = [
            str(self.servers_dir.parent),  # Project root
            str(self.servers_dir),          # servers/
            str(self.skills_dir),           # skills/
        ]

        wrapper = f"""
import sys
import os
from pathlib import Path

# Add directories to Python path
sys.path.insert(0, r"{self.servers_dir.parent / 'src'}")
sys.path.insert(0, r"{self.servers_dir}")
sys.path.insert(0, r"{self.skills_dir}")

# Change to project root
os.chdir(r"{self.servers_dir.parent}")

# Import runtime
from mcp_skill_framework.runtime import _runtime_instance

# Verify runtime is available
if _runtime_instance is None:
    print("ERROR: MCP Runtime not initialized", file=sys.stderr)
    sys.exit(1)

# Execute user code
try:
    # User code starts here
{self._indent_code(code, 4)}
    # User code ends here
except Exception as e:
    import traceback
    print("ERROR:", str(e), file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
"""
        return wrapper

    def _indent_code(self, code: str, spaces: int) -> str:
        """
        Indent code by specified number of spaces.

        Args:
            code: Code to indent
            spaces: Number of spaces

        Returns:
            Indented code
        """
        indent = " " * spaces
        lines = code.split('\n')
        return '\n'.join(indent + line if line.strip() else line for line in lines)

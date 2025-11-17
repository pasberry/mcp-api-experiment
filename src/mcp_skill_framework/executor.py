"""
Code Executor - Runs agent code in sandboxed Docker environment.
"""

from typing import Any, Optional, Dict
from pathlib import Path
import logging
import subprocess
import sys
import tempfile
import json
import docker
from docker.errors import DockerException, ImageNotFound

logger = logging.getLogger(__name__)


class CodeExecutor:
    """
    Executes agent code in isolated Docker environment.

    This component:
    1. Prepares Docker execution environment with access to servers/ and skills/
    2. Executes code safely in Docker container
    3. Returns results to agent
    4. Falls back to subprocess if Docker is unavailable
    """

    IMAGE_NAME = "mcp-skill-framework-executor"
    IMAGE_TAG = "latest"

    def __init__(
        self,
        servers_dir: Path,
        skills_dir: Path,
        tasks_dir: Path,
        runtime: Any,
        use_docker: bool = True,
        telemetry: Any = None,
    ):
        """
        Initialize code executor.

        Args:
            servers_dir: Path to generated server APIs
            skills_dir: Path to agent skills
            tasks_dir: Path to task checkpoints
            runtime: MCPRuntime instance
            use_docker: Whether to use Docker (falls back to subprocess if False or Docker unavailable)
            telemetry: TelemetryLogger instance for logging execution events
        """
        self.servers_dir = servers_dir.resolve()
        self.skills_dir = skills_dir.resolve()
        self.tasks_dir = tasks_dir.resolve()
        self.runtime = runtime
        self.use_docker = use_docker
        self.telemetry = telemetry
        self.docker_client = None
        self.docker_available = False

        # Try to initialize Docker
        if self.use_docker:
            self._init_docker()

    def _init_docker(self) -> None:
        """Initialize Docker client and ensure image exists."""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            self.docker_available = True
            logger.info("Docker is available")

            # Check if image exists, build if not
            self._ensure_image()

        except DockerException as e:
            logger.warning(f"Docker not available: {e}. Falling back to subprocess.")
            self.docker_available = False
            self.docker_client = None

    def _ensure_image(self) -> None:
        """Ensure Docker image exists, build if necessary."""
        try:
            self.docker_client.images.get(f"{self.IMAGE_NAME}:{self.IMAGE_TAG}")
            logger.info(f"Docker image {self.IMAGE_NAME}:{self.IMAGE_TAG} found")
        except ImageNotFound:
            logger.info(f"Building Docker image {self.IMAGE_NAME}:{self.IMAGE_TAG}...")
            dockerfile_path = self.servers_dir.parent / "docker"
            if not dockerfile_path.exists():
                logger.warning("Dockerfile not found, falling back to subprocess")
                self.docker_available = False
                return

            try:
                self.docker_client.images.build(
                    path=str(self.servers_dir.parent),
                    dockerfile=str(dockerfile_path / "Dockerfile"),
                    tag=f"{self.IMAGE_NAME}:{self.IMAGE_TAG}",
                    rm=True
                )
                logger.info("Docker image built successfully")
            except Exception as e:
                logger.error(f"Failed to build Docker image: {e}")
                self.docker_available = False

    def execute(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute code in sandboxed environment (Docker or subprocess).

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: 'success', 'result', 'stdout', 'stderr'
        """
        import time

        # Count lines for telemetry
        code_lines = len(code.split('\n'))
        mode = "docker" if self.docker_available else "subprocess"

        start_time = time.time()

        if self.docker_available:
            logger.info("Executing code in Docker container...")
            result = self._execute_docker(code, timeout)
        else:
            logger.info("Executing code in subprocess...")
            result = self._execute_subprocess(code, timeout)

        duration_ms = (time.time() - start_time) * 1000

        # Log telemetry
        if self.telemetry:
            self.telemetry.log_code_execution(
                mode=mode,
                code_lines=code_lines,
                success=result.get('success', False),
                duration_ms=duration_ms,
                return_value=result.get('return_value'),
                error=result.get('error'),
            )

        return result

    def _execute_docker(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        Execute code in Docker container.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: 'success', 'result', 'stdout', 'stderr'
        """
        try:
            # Create wrapper script for Docker
            wrapper_code = self._create_wrapper(code, docker_mode=True)

            # Write to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                dir=str(self.servers_dir.parent / "tmp")
            ) as f:
                f.write(wrapper_code)
                temp_file = Path(f.name)

            try:
                # Create tmp directory if it doesn't exist
                (self.servers_dir.parent / "tmp").mkdir(exist_ok=True)

                # Run container
                result = self.docker_client.containers.run(
                    image=f"{self.IMAGE_NAME}:{self.IMAGE_TAG}",
                    command=["python", f"/workspace/tmp/{temp_file.name}"],
                    volumes={
                        str(self.servers_dir.parent / "src"): {
                            'bind': '/workspace/src',
                            'mode': 'ro'
                        },
                        str(self.servers_dir): {
                            'bind': '/workspace/servers',
                            'mode': 'ro'
                        },
                        str(self.skills_dir): {
                            'bind': '/workspace/skills',
                            'mode': 'rw'
                        },
                        str(self.tasks_dir): {
                            'bind': '/workspace/tasks',
                            'mode': 'rw'
                        },
                        str(self.servers_dir.parent / "tmp"): {
                            'bind': '/workspace/tmp',
                            'mode': 'rw'
                        },
                    },
                    network_mode='host',  # Allow access to host network
                    remove=True,  # Auto-remove container after execution
                    mem_limit='512m',  # Memory limit
                    cpu_period=100000,  # CPU limits
                    cpu_quota=50000,  # 50% of one CPU
                    working_dir='/workspace',
                    environment={
                        'PYTHONPATH': '/workspace/src:/workspace',
                    },
                    detach=False,
                    stdout=True,
                    stderr=True,
                    timeout=timeout,
                )

                # Decode result
                output = result.decode('utf-8') if isinstance(result, bytes) else result

                # Parse JSON result from output
                return self._parse_result(output)

            except docker.errors.ContainerError as e:
                return {
                    'success': False,
                    'result': None,
                    'stdout': e.stdout.decode('utf-8') if e.stdout else '',
                    'stderr': e.stderr.decode('utf-8') if e.stderr else '',
                    'error': f"Container error: {e}",
                }
            finally:
                # Clean up temp file
                temp_file.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Docker execution failed: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
            }

    def _execute_subprocess(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        Execute code in subprocess (fallback when Docker unavailable).

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: 'success', 'result', 'stdout', 'stderr'
        """
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

                # Parse JSON result from stdout
                return self._parse_result(result.stdout)

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

    def _create_wrapper(self, code: str, docker_mode: bool = False) -> str:
        """
        Create wrapper script that sets up execution environment.

        Args:
            code: User code to execute
            docker_mode: Whether running in Docker (uses /workspace paths)

        Returns:
            Wrapper code
        """
        if docker_mode:
            # Docker paths
            src_path = "/workspace/src"
            servers_path = "/workspace/servers"
            skills_path = "/workspace/skills"
            work_dir = "/workspace"
        else:
            # Host paths
            src_path = str(self.servers_dir.parent / 'src')
            servers_path = str(self.servers_dir)
            skills_path = str(self.skills_dir)
            work_dir = str(self.servers_dir.parent)

        wrapper = f"""
import sys
import os
import json
import traceback
import time
from pathlib import Path
from io import StringIO

# Add directories to Python path
sys.path.insert(0, r"{src_path}")
sys.path.insert(0, r"{servers_path}")
sys.path.insert(0, r"{skills_path}")

# Change to project root
os.chdir(r"{work_dir}")

# Import runtime (but don't check if initialized yet - will check on actual mcp_call)
try:
    from mcp_skill_framework.runtime import _runtime_instance, mcp_call
except ImportError:
    # Runtime not available - mcp_call will fail if used
    _runtime_instance = None
    def mcp_call(*args, **kwargs):
        raise RuntimeError("MCP Runtime not available in execution environment")

# Capture stdout/stderr
stdout_capture = StringIO()
stderr_capture = StringIO()
original_stdout = sys.stdout
original_stderr = sys.stderr

# Result structure
result = {{
    "success": False,
    "return_value": None,
    "stdout": "",
    "stderr": "",
    "error": None,
    "execution_time_ms": 0,
    "exit_code": 0
}}

try:
    # Redirect stdout/stderr
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture

    # Start timer
    start_time = time.time()

    # Execute user code and capture return value
    # Create a namespace for execution
    exec_namespace = {{
        '__name__': '__main__',
        '__builtins__': __builtins__,
    }}

    # Execute the code
    exec(compile('''
{self._indent_code(code, 0)}
''', '<agent_code>', 'exec'), exec_namespace)

    # Try to get return value from last expression or __result__
    return_value = exec_namespace.get('__result__')

    # If no explicit __result__, try to find the last assigned variable
    # or the result of the last function definition
    if return_value is None:
        # Look for common result variable names
        for var_name in ['result', 'output', 'answer', 'data']:
            if var_name in exec_namespace:
                return_value = exec_namespace[var_name]
                break

    # Calculate execution time
    execution_time = (time.time() - start_time) * 1000

    # Restore stdout/stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr

    # Build success result
    result["success"] = True
    result["return_value"] = return_value
    result["stdout"] = stdout_capture.getvalue()
    result["stderr"] = stderr_capture.getvalue()
    result["execution_time_ms"] = execution_time
    result["exit_code"] = 0

except Exception as e:
    # Calculate execution time
    execution_time = (time.time() - start_time) * 1000

    # Restore stdout/stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr

    # Get traceback info
    tb = traceback.extract_tb(sys.exc_info()[2])

    # Find the frame that corresponds to user code
    user_code_frame = None
    for frame in tb:
        if frame.filename == '<agent_code>':
            user_code_frame = frame
            break

    # Build error result
    result["success"] = False
    result["return_value"] = None
    result["stdout"] = stdout_capture.getvalue()
    result["stderr"] = stderr_capture.getvalue()
    result["error"] = {{
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc(),
        "line_number": user_code_frame.lineno if user_code_frame else None,
        "code_context": user_code_frame.line if user_code_frame else None
    }}
    result["execution_time_ms"] = execution_time
    result["exit_code"] = 1

# Output result as JSON
print("__RESULT_START__")
print(json.dumps(result, default=str))  # default=str handles non-serializable types
print("__RESULT_END__")
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

    def _parse_result(self, output: str) -> Dict[str, Any]:
        """
        Extract JSON result from stdout between markers.

        Args:
            output: Raw stdout containing JSON result

        Returns:
            Parsed result dictionary
        """
        try:
            start_marker = "__RESULT_START__"
            end_marker = "__RESULT_END__"
            start_idx = output.find(start_marker)
            end_idx = output.find(end_marker)

            if start_idx == -1 or end_idx == -1:
                # Fallback if markers not found
                logger.warning("Result markers not found in output")
                return {
                    "success": False,
                    "return_value": None,
                    "stdout": output,
                    "stderr": "",
                    "error": {
                        "type": "ParseError",
                        "message": "Could not find result markers in output",
                        "traceback": "",
                        "line_number": None,
                        "code_context": None
                    },
                    "execution_time_ms": 0,
                    "exit_code": 1
                }

            # Extract JSON between markers
            json_str = output[start_idx + len(start_marker):end_idx].strip()
            result = json.loads(json_str)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON result: {e}")
            return {
                "success": False,
                "return_value": None,
                "stdout": output,
                "stderr": "",
                "error": {
                    "type": "JSONDecodeError",
                    "message": f"Failed to parse result JSON: {str(e)}",
                    "traceback": "",
                    "line_number": None,
                    "code_context": None
                },
                "execution_time_ms": 0,
                "exit_code": 1
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing result: {e}")
            return {
                "success": False,
                "return_value": None,
                "stdout": output,
                "stderr": "",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": "",
                    "line_number": None,
                    "code_context": None
                },
                "execution_time_ms": 0,
                "exit_code": 1
            }

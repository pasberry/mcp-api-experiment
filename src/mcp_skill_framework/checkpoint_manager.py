"""
Checkpoint Manager - Saves and resumes task state as code.
"""

from typing import Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages task checkpoints.

    This component:
    1. Serializes state as Python code
    2. Saves checkpoints with metadata
    3. Resumes tasks from checkpoints
    """

    def __init__(self, tasks_dir: Path):
        """
        Initialize checkpoint manager.

        Args:
            tasks_dir: Directory to store checkpoints
        """
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        task_id: str,
        state: Dict[str, Any],
        code: str,
        description: str = "",
    ) -> None:
        """
        Create a checkpoint for a task.

        Creates:
        - tasks/{task_id}/README.md
        - tasks/{task_id}/checkpoint.py
        - tasks/{task_id}/.meta.json
        - tasks/{task_id}/data/

        Args:
            task_id: Unique task identifier
            state: State dict to serialize
            code: Resume code
            description: Optional task description
        """
        logger.info(f"Creating checkpoint: {task_id}")

        # Create task directory
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create data directory
        data_dir = task_dir / "data"
        data_dir.mkdir(exist_ok=True)

        # Serialize state as Python code
        state_code = self._serialize_state_as_code(state)

        # Create checkpoint.py
        checkpoint_code = f'''"""
Checkpoint for task: {task_id}
Description: {description}
Created: {datetime.now().isoformat()}
"""

# Task state
{state_code}

# Resume function
def resume():
    """Resume task execution from this checkpoint."""
{self._indent_code(code, 4)}

if __name__ == "__main__":
    result = resume()
    print(f"Resume completed: {{result}}")
'''

        checkpoint_path = task_dir / "checkpoint.py"
        checkpoint_path.write_text(checkpoint_code)

        # Generate README
        readme_content = f"""# Task: {task_id}

**Status:** Active
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Description

{description or 'No description provided.'}

## State

See `checkpoint.py` for full state details.

## Resume

To resume this task:

```python
from tasks.{task_id}.checkpoint import resume

result = resume()
```
"""

        readme_path = task_dir / "README.md"
        readme_path.write_text(readme_content)

        # Generate metadata
        metadata = self._generate_checkpoint_metadata(task_id, description)
        meta_path = task_dir / ".meta.json"
        meta_path.write_text(json.dumps(metadata, indent=2))

        logger.info(f"Checkpoint created: {task_dir}")

    def resume_checkpoint(self, task_id: str) -> Any:
        """
        Resume from a checkpoint.

        Loads checkpoint.py and executes resume() function.

        Args:
            task_id: Task identifier

        Returns:
            Result of resume execution
        """
        logger.info(f"Resuming checkpoint: {task_id}")

        task_dir = self.tasks_dir / task_id
        checkpoint_path = task_dir / "checkpoint.py"

        if not checkpoint_path.exists():
            raise ValueError(f"Checkpoint not found: {task_id}")

        # Load and execute checkpoint
        import importlib.util
        spec = importlib.util.spec_from_file_location("checkpoint", checkpoint_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, 'resume'):
                result = module.resume()
                logger.info(f"Checkpoint resumed successfully: {task_id}")
                return result
            else:
                raise ValueError(f"Checkpoint has no resume() function: {task_id}")
        else:
            raise ValueError(f"Failed to load checkpoint: {task_id}")

    def list_checkpoints(self) -> list:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint metadata
        """
        checkpoints = []

        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            meta_path = task_dir / ".meta.json"
            if meta_path.exists():
                try:
                    metadata = json.loads(meta_path.read_text())
                    checkpoints.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint metadata for {task_dir}: {e}")

        return checkpoints

    def _serialize_state_as_code(self, state: Dict[str, Any]) -> str:
        """
        Convert state dict to Python code.

        Args:
            state: State dictionary

        Returns:
            Python code representing state
        """
        import pprint

        lines = []
        for key, value in state.items():
            # Use pprint for nice formatting
            value_repr = pprint.pformat(value, width=80, compact=True)
            lines.append(f"{key} = {value_repr}")

        return "\n".join(lines)

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

    def _generate_checkpoint_metadata(
        self,
        task_id: str,
        description: str,
    ) -> Dict[str, Any]:
        """
        Generate metadata for checkpoint.

        Args:
            task_id: Task identifier
            description: Task description

        Returns:
            Metadata dict
        """
        return {
            "task_id": task_id,
            "description": description,
            "created": datetime.now().isoformat(),
            "status": "active",
        }

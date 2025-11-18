"""Test utilities for MCP Skill Framework."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil


class TempTestEnvironment:
    """Context manager for temporary test environment."""

    def __init__(self):
        """Initialize temp environment."""
        self.tmpdir = None
        self.servers_dir = None
        self.skills_dir = None
        self.db_path = None

    def __enter__(self):
        """Set up temporary directories."""
        self.tmpdir = tempfile.mkdtemp()
        tmppath = Path(self.tmpdir)

        self.servers_dir = tmppath / "servers"
        self.skills_dir = tmppath / "skills"
        self.db_path = tmppath / "skills.db"

        self.servers_dir.mkdir()
        self.skills_dir.mkdir()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary directories."""
        if self.tmpdir and Path(self.tmpdir).exists():
            shutil.rmtree(self.tmpdir)


def create_test_config(
    servers: List[Dict[str, str]], output_path: Optional[Path] = None
) -> Path:
    """
    Create a test MCP servers config file.

    Args:
        servers: List of server configs
        output_path: Where to write config (or temp file if None)

    Returns:
        Path to config file
    """
    config = {"servers": servers}

    if output_path is None:
        fd, path = tempfile.mkstemp(suffix=".json")
        output_path = Path(path)
        # Close the file descriptor since we'll write with json.dump
        import os

        os.close(fd)

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    return output_path


def create_test_skill(
    skills_dir: Path,
    category: str,
    name: str,
    code: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Create a test skill on filesystem.

    Args:
        skills_dir: Skills directory
        category: Skill category
        name: Skill name
        code: Skill code
        metadata: Optional metadata dict

    Returns:
        Path to skill directory
    """
    skill_dir = skills_dir / category / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Write main.py
    (skill_dir / "main.py").write_text(code)

    # Write README.md
    readme = f"# {name}\n\n{metadata.get('description', 'Test skill')}\n"
    (skill_dir / "README.md").write_text(readme)

    # Write __init__.py
    (skill_dir / "__init__.py").write_text(
        f"from .main import *\n__all__ = ['{name}']\n"
    )

    # Write .meta.json
    if metadata is None:
        metadata = {}

    meta = {
        "name": name,
        "category": category,
        "created_at": "2024-01-01T00:00:00",
        "tags": metadata.get("tags", []),
        "dependencies": metadata.get("dependencies", []),
        "description": metadata.get("description", "Test skill"),
    }

    (skill_dir / ".meta.json").write_text(json.dumps(meta, indent=2))

    return skill_dir


def load_fixture(fixture_name: str) -> str:
    """
    Load a test fixture file.

    Args:
        fixture_name: Name of fixture (e.g., "skills/simple_skill.py")

    Returns:
        File contents as string
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    return fixture_path.read_text()


def load_json_fixture(fixture_name: str) -> Dict[str, Any]:
    """
    Load a JSON test fixture.

    Args:
        fixture_name: Name of fixture (e.g., "configs/valid-single-server.json")

    Returns:
        Parsed JSON dict
    """
    content = load_fixture(fixture_name)
    return json.loads(content)

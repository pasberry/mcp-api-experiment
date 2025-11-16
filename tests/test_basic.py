"""
Basic tests for MCP Skill Framework
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from mcp_skill_framework import MCPApi
from mcp_skill_framework.skill_manager import SkillManager
from mcp_skill_framework.checkpoint_manager import CheckpointManager


class TestSkillManager:
    """Test skill management functionality."""

    def test_save_and_list_skills(self):
        """Test saving and listing skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            manager = SkillManager(skills_dir)

            # Save a skill
            code = '''
def hello():
    """Say hello."""
    return "Hello, World!"
'''
            manager.save_skill(code, "hello", "greetings", tags=["test"])

            # List skills
            skills = manager.list_skills()
            assert len(skills) == 1
            assert skills[0]['name'] == 'hello'
            assert skills[0]['category'] == 'greetings'

            # Get skill info
            info = manager.get_skill_info("greetings", "hello")
            assert 'code' in info
            assert 'readme' in info

    def test_skill_directory_structure(self):
        """Test that skills are created with proper structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            manager = SkillManager(skills_dir)

            code = 'def test(): pass'
            manager.save_skill(code, "test_skill", "category")

            skill_dir = skills_dir / "category" / "test_skill"
            assert (skill_dir / "main.py").exists()
            assert (skill_dir / "README.md").exists()
            assert (skill_dir / "__init__.py").exists()
            assert (skill_dir / ".meta.json").exists()


class TestCheckpointManager:
    """Test checkpoint management functionality."""

    def test_create_and_list_checkpoints(self):
        """Test creating and listing checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = Path(tmpdir) / "tasks"
            manager = CheckpointManager(tasks_dir)

            # Create checkpoint
            state = {"counter": 42, "items": ["a", "b", "c"]}
            code = "return counter + len(items)"
            manager.create_checkpoint("test_task", state, code, "Test task")

            # List checkpoints
            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 1
            assert checkpoints[0]['task_id'] == 'test_task'

    def test_checkpoint_directory_structure(self):
        """Test that checkpoints are created with proper structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = Path(tmpdir) / "tasks"
            manager = CheckpointManager(tasks_dir)

            state = {"value": 123}
            code = "return value"
            manager.create_checkpoint("task1", state, code)

            task_dir = tasks_dir / "task1"
            assert (task_dir / "checkpoint.py").exists()
            assert (task_dir / "README.md").exists()
            assert (task_dir / ".meta.json").exists()
            assert (task_dir / "data").is_dir()


class TestMCPApi:
    """Test MCPApi integration."""

    def test_api_initialization(self):
        """Test that MCPApi initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                tasks_dir=f"{tmpdir}/tasks"
            )

            assert api.servers_dir.exists()
            assert api.skills_dir.exists()
            assert api.tasks_dir.exists()

    def test_add_server(self):
        """Test adding MCP servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                tasks_dir=f"{tmpdir}/tasks"
            )

            # Should not raise
            api.add_mcp_server("test_server", "echo test")
            assert "test_server" in api.connector.servers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

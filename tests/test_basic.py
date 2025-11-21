"""
Basic tests for MCP Skill Framework

Tests the refactored code generation and skill persistence architecture.
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import json

from src import MCPApi, SkillManager, SkillsDatabase


class TestSkillsDatabase:
    """Test skills database functionality."""

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test that database initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)

            await db.initialize()

            assert db_path.exists()
            assert db._initialized

    @pytest.mark.asyncio
    async def test_save_and_retrieve_skill(self):
        """Test saving and retrieving a skill from database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save a skill
            code = '''
def hello():
    """Say hello."""
    return "Hello, World!"
'''
            dependencies = [{"server": "test", "tool": "echo"}]
            metadata = {"tags": ["test"], "description": "Test skill"}

            await db.save_skill(
                agent_name="test-agent",
                skill_name="hello",
                category="greetings",
                code=code,
                dependencies=dependencies,
                metadata=metadata
            )

            # Retrieve the skill
            skill = await db.get_skill("test-agent", "hello")

            assert skill is not None
            assert skill['skill_name'] == 'hello'
            assert skill['category'] == 'greetings'
            assert skill['code'] == code
            assert len(skill['dependencies']) == 1
            assert skill['dependencies'][0]['server'] == 'test'

    @pytest.mark.asyncio
    async def test_get_all_skills_for_agent(self):
        """Test retrieving all skills for an agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save multiple skills for same agent
            for i in range(3):
                await db.save_skill(
                    agent_name="test-agent",
                    skill_name=f"skill_{i}",
                    category="test",
                    code=f"def skill_{i}(): pass"
                )

            # Save skill for different agent
            await db.save_skill(
                agent_name="other-agent",
                skill_name="other_skill",
                category="test",
                code="def other(): pass"
            )

            # Get skills for test-agent
            skills = await db.get_all_skills("test-agent")

            assert len(skills) == 3
            assert all(s['agent_name'] == 'test-agent' for s in skills)

    @pytest.mark.asyncio
    async def test_agent_stats(self):
        """Test getting statistics for an agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"
            db = SkillsDatabase(db_path)
            await db.initialize()

            # Save skills in different categories
            await db.save_skill("test-agent", "skill1", "data_sync", "pass")
            await db.save_skill("test-agent", "skill2", "data_sync", "pass")
            await db.save_skill("test-agent", "skill3", "analysis", "pass")

            stats = await db.get_agent_stats("test-agent")

            assert stats['total_skills'] == 3
            assert stats['by_category']['data_sync'] == 2
            assert stats['by_category']['analysis'] == 1


class TestSkillManager:
    """Test skill manager functionality."""

    def test_save_skill_to_filesystem(self):
        """Test saving a skill to filesystem (synchronous part)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
                telemetry=None
            )

            code = '''
def hello():
    """Say hello."""
    return "Hello, World!"
'''
            # Save skill (don't persist to DB in this test)
            manager.save_skill(code, "hello", "greetings", tags=["test"], persist_to_db=False)

            # Check filesystem structure
            skill_dir = skills_dir / "greetings" / "hello"
            assert skill_dir.exists()
            assert (skill_dir / "main.py").exists()
            assert (skill_dir / "README.md").exists()
            assert (skill_dir / "__init__.py").exists()
            assert (skill_dir / ".meta.json").exists()

            # Verify metadata
            meta = json.loads((skill_dir / ".meta.json").read_text())
            assert meta['name'] == 'hello'
            assert meta['category'] == 'greetings'
            assert 'test' in meta['tags']

    def test_list_skills_from_filesystem(self):
        """Test listing skills from filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path
            )

            # Save multiple skills
            manager.save_skill("def skill1(): pass", "skill1", "cat1", persist_to_db=False)
            manager.save_skill("def skill2(): pass", "skill2", "cat1", persist_to_db=False)
            manager.save_skill("def skill3(): pass", "skill3", "cat2", persist_to_db=False)

            # List all skills
            all_skills = manager.list_skills()
            assert len(all_skills) == 3

            # List skills by category
            cat1_skills = manager.list_skills(category="cat1")
            assert len(cat1_skills) == 2

    def test_dependency_extraction(self):
        """Test that MCP tool dependencies are extracted from code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path
            )

            code = '''
def backup_files(folder_id):
    files = mcp_call('google-drive', 'list_files', {'folder_id': folder_id})
    for file in files:
        content = mcp_call('google-drive', 'download_file', {'file_id': file['id']})
    return len(files)
'''
            manager.save_skill(code, "backup", "data_sync", persist_to_db=False)

            # Check dependencies in metadata
            skill_dir = skills_dir / "data_sync" / "backup"
            meta = json.loads((skill_dir / ".meta.json").read_text())

            assert len(meta['dependencies']) == 2
            deps = {(d['server'], d['tool']) for d in meta['dependencies']}
            assert ('google-drive', 'list_files') in deps
            assert ('google-drive', 'download_file') in deps

    @pytest.mark.asyncio
    async def test_hydration_from_database(self):
        """Test hydrating skills from database to filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            # Setup database with skills
            db = SkillsDatabase(db_path)
            await db.initialize()

            await db.save_skill(
                agent_name="test-agent",
                skill_name="skill1",
                category="test",
                code="def skill1(): pass"
            )
            await db.save_skill(
                agent_name="test-agent",
                skill_name="skill2",
                category="test",
                code="def skill2(): pass"
            )

            # Create manager and hydrate
            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path
            )

            count = await manager.hydrate_from_database()

            assert count == 2
            assert (skills_dir / "test" / "skill1" / "main.py").exists()
            assert (skills_dir / "test" / "skill2" / "main.py").exists()


class TestMCPApi:
    """Test MCPApi integration."""

    def test_api_initialization(self):
        """Test that MCPApi initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None  # Disable telemetry for tests
            )

            assert api.agent_name == "test-agent"
            assert api.servers_dir.exists()
            assert api.skills_dir.exists()
            assert api.telemetry is None

    def test_add_mcp_server(self):
        """Test adding MCP servers for code generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None
            )

            # Should not raise
            api.add_mcp_server("test_server", "echo test")
            assert "test_server" in api.connector.servers

    def test_save_skill(self):
        """Test saving a skill through the API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=f"{tmpdir}/skills.db",
                telemetry_db=None
            )

            code = "def test_skill(): return 42"
            # Don't persist to DB in this test - only testing filesystem
            api.save_skill(code, "test_skill", "test", persist_to_db=False)

            # Verify skill was saved to filesystem
            skills = api.list_skills()
            assert len(skills) == 1
            assert skills[0]['name'] == 'test_skill'

    @pytest.mark.asyncio
    async def test_hydrate_skills(self):
        """Test hydrating skills on API startup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"

            # Pre-populate database
            db = SkillsDatabase(db_path)
            await db.initialize()
            await db.save_skill(
                agent_name="test-agent",
                skill_name="existing_skill",
                category="test",
                code="def existing(): pass"
            )

            # Create API and hydrate
            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=str(db_path),
                telemetry_db=None
            )

            count = await api.hydrate_skills()

            assert count == 1
            skills = api.list_skills()
            assert len(skills) == 1
            assert skills[0]['name'] == 'existing_skill'

    @pytest.mark.asyncio
    async def test_get_skill_stats(self):
        """Test getting skill statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "skills.db"

            # Pre-populate database
            db = SkillsDatabase(db_path)
            await db.initialize()
            await db.save_skill("test-agent", "skill1", "cat1", "pass")
            await db.save_skill("test-agent", "skill2", "cat2", "pass")

            api = MCPApi(
                agent_name="test-agent",
                servers_dir=f"{tmpdir}/servers",
                skills_dir=f"{tmpdir}/skills",
                skills_db=str(db_path),
                telemetry_db=None
            )

            stats = await api.get_skill_stats()

            assert stats['total_skills'] == 2
            assert stats['agent_name'] == 'test-agent'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

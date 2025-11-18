"""
Extended tests for SkillManager - Edge cases and error handling.

Tests additional edge cases, error handling, and untested paths in Skill Manager.
"""

import pytest
import tempfile
import json
from pathlib import Path

from mcp_skill_framework import SkillManager, SkillsDatabase


class TestSkillManagerEdgeCases:
    """Test edge cases in skill manager."""

    def test_get_skill_categories_empty(self):
        """Test getting categories when no skills exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            categories = manager.get_skill_categories()

            assert categories == []

    def test_get_skill_categories_with_skills(self):
        """Test getting categories with multiple categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            # Create skills in different categories
            manager.save_skill("def s1(): pass", "skill1", "data_sync", persist_to_db=False)
            manager.save_skill("def s2(): pass", "skill2", "data_sync", persist_to_db=False)
            manager.save_skill("def s3(): pass", "skill3", "analysis", persist_to_db=False)

            categories = manager.get_skill_categories()

            assert len(categories) == 2
            # Find categories by name
            data_sync = [c for c in categories if c["name"] == "data_sync"][0]
            analysis = [c for c in categories if c["name"] == "analysis"][0]

            assert data_sync["count"] == 2
            assert analysis["count"] == 1

    def test_list_skills_filters_by_category(self):
        """Test that list_skills correctly filters by category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            # Create skills in different categories
            manager.save_skill("def s1(): pass", "skill1", "cat1", persist_to_db=False)
            manager.save_skill("def s2(): pass", "skill2", "cat1", persist_to_db=False)
            manager.save_skill("def s3(): pass", "skill3", "cat2", persist_to_db=False)

            # Filter by cat1
            cat1_skills = manager.list_skills(category="cat1")

            assert len(cat1_skills) == 2
            assert all(s["category"] == "cat1" for s in cat1_skills)

    def test_dependency_extraction_with_no_mcp_calls(self):
        """Test dependency extraction when code has no mcp_call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            code = """
def pure_function(x, y):
    return x + y
"""

            manager.save_skill(code, "pure", "utils", persist_to_db=False)

            meta_path = skills_dir / "utils" / "pure" / ".meta.json"
            meta = json.loads(meta_path.read_text())

            assert meta["dependencies"] == []

    def test_dependency_extraction_with_multiple_calls(self):
        """Test extracting multiple dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            code = """
def complex_task():
    users = mcp_call('github', 'list_users', {})
    for user in users:
        repos = mcp_call('github', 'list_repos', {'user': user})
        for repo in repos:
            files = mcp_call('filesystem', 'list_files', {'path': repo})
    return users
"""

            manager.save_skill(code, "complex", "sync", persist_to_db=False)

            meta_path = skills_dir / "sync" / "complex" / ".meta.json"
            meta = json.loads(meta_path.read_text())

            # Should have 3 unique dependencies
            assert len(meta["dependencies"]) == 3

            deps_set = {(d["server"], d["tool"]) for d in meta["dependencies"]}
            assert ("github", "list_users") in deps_set
            assert ("github", "list_repos") in deps_set
            assert ("filesystem", "list_files") in deps_set

    @pytest.mark.asyncio
    async def test_hydrate_from_database_with_none_metadata(self):
        """Test hydration when database has None metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            # Pre-populate database with None values
            db = SkillsDatabase(db_path)
            await db.initialize()

            await db.save_skill(
                agent_name="test-agent",
                skill_name="skill1",
                category="test",
                code="def test(): pass",
                dependencies=None,  # None in database
                metadata=None,  # None in database
            )

            # Create manager and hydrate
            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            # Should not raise - None values should be handled
            count = await manager.hydrate_from_database()

            assert count == 1
            assert (skills_dir / "test" / "skill1" / "main.py").exists()

    @pytest.mark.asyncio
    async def test_hydrate_clears_existing_skills(self):
        """Test that hydration clears existing skills directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            # Create some existing skills on filesystem
            skills_dir.mkdir()
            old_skill_dir = skills_dir / "old_category" / "old_skill"
            old_skill_dir.mkdir(parents=True)
            (old_skill_dir / "main.py").write_text("# old skill")

            # Populate database with new skill
            db = SkillsDatabase(db_path)
            await db.initialize()
            await db.save_skill(
                agent_name="test-agent",
                skill_name="new_skill",
                category="new_category",
                code="def new(): pass",
            )

            # Create manager and hydrate
            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            await manager.hydrate_from_database()

            # Old skill should be gone
            assert not (skills_dir / "old_category").exists()

            # New skill should exist
            assert (skills_dir / "new_category" / "new_skill" / "main.py").exists()

    @pytest.mark.asyncio
    async def test_persist_to_database_async(self):
        """Test async persistence to database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            # Initialize database
            db = SkillsDatabase(db_path)
            await db.initialize()

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            # Persist skill
            await manager._persist_to_database(
                name="test_skill",
                category="test",
                code="def test(): pass",
                dependencies=[],
                metadata={},
            )

            # Verify in database
            skill = await db.get_skill("test-agent", "test_skill")

            assert skill is not None
            assert skill["skill_name"] == "test_skill"
            assert skill["category"] == "test"
            assert skill["code"] == "def test(): pass"

    def test_create_skills_directory_if_not_exists(self):
        """Test that skills directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create skills_dir
            skills_dir = Path(tmpdir) / "skills"
            db_path = Path(tmpdir) / "skills.db"

            assert not skills_dir.exists()

            manager = SkillManager(
                skills_dir=skills_dir,
                agent_name="test-agent",
                db_path=db_path,
            )

            # Should create directory when saving
            manager.save_skill(
                code="def test(): pass",
                name="test",
                category="test",
                persist_to_db=False,
            )

            assert skills_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

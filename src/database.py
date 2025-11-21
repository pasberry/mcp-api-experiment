"""
Skills Database - Persistent storage for agent skills.

Provides async database operations for storing and retrieving
agent skills across sessions.
"""

import aiosqlite
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillsDatabase:
    """
    Async SQLite database for storing agent skills.

    Schema:
        skills(
            agent_name TEXT,
            skill_name TEXT,
            category TEXT,
            code TEXT,
            created_at TEXT,
            updated_at TEXT,
            dependencies TEXT,  -- JSON
            metadata TEXT,      -- JSON
            PRIMARY KEY (agent_name, skill_name)
        )
    """

    def __init__(self, db_path: Path):
        """
        Initialize skills database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    agent_name TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    code TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    dependencies TEXT,
                    metadata TEXT,
                    PRIMARY KEY (agent_name, skill_name)
                )
            """)

            # Create index for fast agent lookup
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_skills
                ON skills(agent_name)
            """)

            await db.commit()

        self._initialized = True
        logger.info(f"Skills database initialized: {self.db_path}")

    async def get_all_skills(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get all skills for an agent.

        Args:
            agent_name: Agent identifier

        Returns:
            List of skill dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM skills WHERE agent_name = ? ORDER BY category, skill_name",
                (agent_name,)
            ) as cursor:
                rows = await cursor.fetchall()

        skills = []
        for row in rows:
            skill = dict(row)
            # Parse JSON fields
            if skill.get('dependencies'):
                skill['dependencies'] = json.loads(skill['dependencies'])
            if skill.get('metadata'):
                skill['metadata'] = json.loads(skill['metadata'])
            skills.append(skill)

        logger.info(f"Retrieved {len(skills)} skills for agent '{agent_name}'")
        return skills

    async def get_skill(
        self,
        agent_name: str,
        skill_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific skill.

        Args:
            agent_name: Agent identifier
            skill_name: Skill name

        Returns:
            Skill dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM skills WHERE agent_name = ? AND skill_name = ?",
                (agent_name, skill_name)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        skill = dict(row)
        # Parse JSON fields
        if skill.get('dependencies'):
            skill['dependencies'] = json.loads(skill['dependencies'])
        if skill.get('metadata'):
            skill['metadata'] = json.loads(skill['metadata'])

        return skill

    async def save_skill(
        self,
        agent_name: str,
        skill_name: str,
        category: str,
        code: str,
        dependencies: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save or update a skill.

        Args:
            agent_name: Agent identifier
            skill_name: Skill name
            category: Skill category
            code: Skill code
            dependencies: List of MCP tool dependencies
            metadata: Additional metadata
        """
        now = datetime.utcnow().isoformat() + 'Z'

        # Check if skill exists
        existing = await self.get_skill(agent_name, skill_name)

        async with aiosqlite.connect(self.db_path) as db:
            if existing:
                # Update existing skill
                await db.execute("""
                    UPDATE skills
                    SET category = ?,
                        code = ?,
                        updated_at = ?,
                        dependencies = ?,
                        metadata = ?
                    WHERE agent_name = ? AND skill_name = ?
                """, (
                    category,
                    code,
                    now,
                    json.dumps(dependencies) if dependencies else None,
                    json.dumps(metadata) if metadata else None,
                    agent_name,
                    skill_name
                ))
                logger.info(f"Updated skill: {agent_name}/{skill_name}")
            else:
                # Insert new skill
                await db.execute("""
                    INSERT INTO skills (
                        agent_name, skill_name, category, code,
                        created_at, updated_at, dependencies, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_name,
                    skill_name,
                    category,
                    code,
                    now,
                    now,
                    json.dumps(dependencies) if dependencies else None,
                    json.dumps(metadata) if metadata else None
                ))
                logger.info(f"Inserted new skill: {agent_name}/{skill_name}")

            await db.commit()

    async def delete_skill(self, agent_name: str, skill_name: str) -> bool:
        """
        Delete a skill.

        Args:
            agent_name: Agent identifier
            skill_name: Skill name

        Returns:
            True if skill was deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM skills WHERE agent_name = ? AND skill_name = ?",
                (agent_name, skill_name)
            )
            await db.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted skill: {agent_name}/{skill_name}")
        else:
            logger.warning(f"Skill not found for deletion: {agent_name}/{skill_name}")

        return deleted

    async def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """
        Get statistics for an agent's skills.

        Args:
            agent_name: Agent identifier

        Returns:
            Stats dictionary with counts by category
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Total count
            async with db.execute(
                "SELECT COUNT(*) as count FROM skills WHERE agent_name = ?",
                (agent_name,)
            ) as cursor:
                row = await cursor.fetchone()
                total = row[0]

            # Count by category
            async with db.execute(
                """SELECT category, COUNT(*) as count
                   FROM skills
                   WHERE agent_name = ?
                   GROUP BY category
                   ORDER BY count DESC""",
                (agent_name,)
            ) as cursor:
                rows = await cursor.fetchall()
                by_category = {row[0]: row[1] for row in rows}

        return {
            "agent_name": agent_name,
            "total_skills": total,
            "by_category": by_category
        }

    async def close(self) -> None:
        """Close database connection (cleanup)."""
        # aiosqlite doesn't maintain persistent connections
        # This is here for API consistency
        logger.info("Skills database closed")

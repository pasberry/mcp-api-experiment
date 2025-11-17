"""
Skill Manager - Persists and manages agent skills.

Provides both filesystem (immediate) and database (async) persistence.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging
import re
import asyncio
import threading
from datetime import datetime

from .database import SkillsDatabase

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Manages skill lifecycle with dual persistence.

    This component:
    1. Hydrates skills from database to filesystem on startup
    2. Immediately writes new skills to filesystem (for agent to use)
    3. Asynchronously persists skills to database (for future hydration)
    4. Extracts and tracks MCP tool dependencies
    """

    def __init__(
        self,
        skills_dir: Path,
        agent_name: str,
        db_path: Path,
        telemetry: Any = None
    ):
        """
        Initialize skill manager.

        Args:
            skills_dir: Directory to store skills on filesystem
            agent_name: Agent identifier for database queries
            db_path: Path to skills database
            telemetry: TelemetryLogger instance for logging skill events
        """
        self.skills_dir = skills_dir
        self.agent_name = agent_name
        self.db = SkillsDatabase(db_path)
        self.telemetry = telemetry
        self._db_initialized = False

    async def initialize(self) -> None:
        """Initialize database (async operation)."""
        if not self._db_initialized:
            await self.db.initialize()
            self._db_initialized = True

    async def hydrate_from_database(self) -> int:
        """
        Hydrate skills from database to filesystem.

        Clears existing skills directory and rebuilds from database.
        Database is the source of truth.

        Returns:
            Number of skills hydrated
        """
        logger.info(f"Hydrating skills for agent '{self.agent_name}' from database")

        # Ensure database is initialized
        await self.initialize()

        # Clear existing skills directory
        if self.skills_dir.exists():
            import shutil
            shutil.rmtree(self.skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # Get all skills from database
        skills = await self.db.get_all_skills(self.agent_name)

        # Write each skill to filesystem
        for skill in skills:
            self._write_to_filesystem(
                name=skill['skill_name'],
                category=skill['category'],
                code=skill['code'],
                dependencies=skill.get('dependencies', []),
                metadata=skill.get('metadata', {})
            )

        logger.info(f"Hydrated {len(skills)} skills from database")

        # Log telemetry
        if self.telemetry:
            self.telemetry.log_event(
                level="INFO",
                event_type="skill_hydration",
                data={
                    "agent_name": self.agent_name,
                    "skills_count": len(skills)
                }
            )

        return len(skills)

    def save_skill(
        self,
        code: str,
        name: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        persist_to_db: bool = True
    ) -> None:
        """
        Save code as a reusable skill.

        Immediately writes to filesystem so agent can import it.
        Optionally persists to database asynchronously.

        Creates:
        - skills/{category}/{name}/main.py
        - skills/{category}/{name}/README.md
        - skills/{category}/{name}/.meta.json

        Args:
            code: Python code to save
            name: Skill name
            category: Skill category
            tags: Optional tags for discovery
            persist_to_db: Whether to async persist to database
        """
        logger.info(f"Saving skill: {category}/{name}")

        # Extract dependencies from code
        dependencies = self._extract_dependencies(code)

        # Build metadata
        metadata = {
            "tags": tags or [],
            "description": self._extract_docstring(code)
        }

        # Immediately write to filesystem
        self._write_to_filesystem(name, category, code, dependencies, metadata)

        logger.info(f"Skill saved to filesystem: {category}/{name}")

        # Log telemetry
        if self.telemetry:
            code_lines = len(code.split('\n'))
            self.telemetry.log_skill_save(
                category=category,
                name=name,
                code_lines=code_lines,
                dependencies=dependencies,
            )

        # Async persist to database (fire and forget)
        if persist_to_db:
            try:
                # Try to create task in running event loop
                asyncio.create_task(
                    self._persist_to_database(name, category, code, dependencies, metadata)
                )
            except RuntimeError:
                # No event loop running - run in background thread
                def run_async():
                    asyncio.run(
                        self._persist_to_database(name, category, code, dependencies, metadata)
                    )
                thread = threading.Thread(target=run_async, daemon=True)
                thread.start()

    async def _persist_to_database(
        self,
        name: str,
        category: str,
        code: str,
        dependencies: List[Dict[str, str]],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Asynchronously persist skill to database.

        Args:
            name: Skill name
            category: Skill category
            code: Skill code
            dependencies: MCP tool dependencies
            metadata: Additional metadata
        """
        try:
            # Ensure database is initialized
            await self.initialize()

            # Save to database
            await self.db.save_skill(
                agent_name=self.agent_name,
                skill_name=name,
                category=category,
                code=code,
                dependencies=dependencies,
                metadata=metadata
            )

            logger.info(f"Skill persisted to database: {self.agent_name}/{name}")

            # Log telemetry
            if self.telemetry:
                self.telemetry.log_event(
                    level="INFO",
                    event_type="skill_db_persist",
                    data={
                        "agent_name": self.agent_name,
                        "skill_name": name,
                        "category": category
                    }
                )

        except Exception as e:
            logger.error(f"Failed to persist skill to database: {e}")
            # Don't raise - this is async background task

    def _write_to_filesystem(
        self,
        name: str,
        category: str,
        code: str,
        dependencies: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Write skill to filesystem as importable package.

        Args:
            name: Skill name
            category: Skill category
            code: Skill code
            dependencies: MCP tool dependencies
            metadata: Additional metadata
        """
        # Normalize None to empty dict/list
        dependencies = dependencies or []
        metadata = metadata or {}

        # Create skill directory
        skill_dir = self.skills_dir / category / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Save main.py
        main_py_path = skill_dir / "main.py"
        main_py_path.write_text(code)

        # Extract docstring and generate README
        docstring = self._extract_docstring(code)
        readme_content = self._generate_readme(
            name, category, docstring, metadata.get('tags', [])
        )
        readme_path = skill_dir / "README.md"
        readme_path.write_text(readme_content)

        # Generate and save metadata (with dependencies)
        file_metadata = {
            "name": name,
            "category": category,
            "created": datetime.now().isoformat(),
            "dependencies": dependencies,
            **metadata
        }
        meta_path = skill_dir / ".meta.json"
        meta_path.write_text(json.dumps(file_metadata, indent=2))

        # Create __init__.py for imports
        init_path = skill_dir / "__init__.py"
        init_path.write_text(f'"""{docstring or name}"""\n\nfrom .main import *\n')

    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available skills from filesystem.

        Args:
            category: Optional category filter

        Returns:
            List of skill metadata dicts
        """
        skills = []

        # Determine which categories to scan
        if category:
            category_dirs = [self.skills_dir / category] if (self.skills_dir / category).exists() else []
        else:
            category_dirs = [d for d in self.skills_dir.iterdir() if d.is_dir()]

        # Scan each category
        for category_dir in category_dirs:
            for skill_dir in category_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                meta_path = skill_dir / ".meta.json"
                if meta_path.exists():
                    try:
                        metadata = json.loads(meta_path.read_text())
                        metadata['path'] = str(skill_dir.relative_to(self.skills_dir))
                        skills.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {skill_dir}: {e}")

        return skills

    def get_skill_info(self, category: str, name: str) -> Dict[str, Any]:
        """
        Get detailed info about a skill from filesystem.

        Args:
            category: Skill category
            name: Skill name

        Returns:
            Skill metadata including README content
        """
        skill_dir = self.skills_dir / category / name

        if not skill_dir.exists():
            raise ValueError(f"Skill not found: {category}/{name}")

        # Load metadata
        meta_path = skill_dir / ".meta.json"
        if not meta_path.exists():
            raise ValueError(f"Skill metadata not found: {category}/{name}")

        metadata = json.loads(meta_path.read_text())

        # Load README
        readme_path = skill_dir / "README.md"
        if readme_path.exists():
            metadata['readme'] = readme_path.read_text()

        # Load code
        main_py_path = skill_dir / "main.py"
        if main_py_path.exists():
            metadata['code'] = main_py_path.read_text()

        return metadata

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about agent's skills in database.

        Returns:
            Stats dictionary with counts by category
        """
        await self.initialize()
        return await self.db.get_agent_stats(self.agent_name)

    def _extract_docstring(self, code: str) -> str:
        """
        Extract docstring from Python code.

        Args:
            code: Python code

        Returns:
            Extracted docstring or empty string
        """
        import ast

        try:
            tree = ast.parse(code)
            docstring = ast.get_docstring(tree)
            return docstring or ""
        except Exception as e:
            logger.warning(f"Failed to extract docstring: {e}")
            return ""

    def _generate_readme(
        self,
        name: str,
        category: str,
        docstring: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Generate README content for a skill.

        Args:
            name: Skill name
            category: Skill category
            docstring: Extracted docstring
            tags: Optional tags

        Returns:
            README markdown content
        """
        readme = f"""# {name}

**Category:** {category}
**Created:** {datetime.now().strftime('%Y-%m-%d')}

## Description

{docstring or 'No description available.'}

## Usage

```python
from skills.{category}.{name} import *

# Use the skill here
```
"""

        if tags:
            readme += f"\n## Tags\n\n{', '.join(tags)}\n"

        return readme

    def _extract_dependencies(self, code: str) -> List[Dict[str, str]]:
        """
        Extract MCP tool dependencies from code.

        Scans for mcp_call() invocations and extracts server/tool names.

        Args:
            code: Python code

        Returns:
            List of dependency dicts with 'server' and 'tool' keys
        """
        dependencies = []

        # Pattern to match: mcp_call('server', 'tool', ...)
        # or mcp_call("server", "tool", ...)
        pattern = r'mcp_call\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'

        matches = re.finditer(pattern, code)
        seen = set()

        for match in matches:
            server = match.group(1)
            tool = match.group(2)
            key = (server, tool)

            if key not in seen:
                dependencies.append({
                    "server": server,
                    "tool": tool,
                })
                seen.add(key)

        return dependencies

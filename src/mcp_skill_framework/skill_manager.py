"""
Skill Manager - Persists and manages agent skills.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Manages skill lifecycle.

    This component:
    1. Saves agent code as skills
    2. Generates README from docstrings
    3. Tracks skill metadata and usage
    4. Provides skill discovery
    """

    def __init__(self, skills_dir: Path, telemetry: Any = None):
        """
        Initialize skill manager.

        Args:
            skills_dir: Directory to store skills
            telemetry: TelemetryLogger instance for logging skill events
        """
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry = telemetry

    def save_skill(
        self,
        code: str,
        name: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Save code as a reusable skill.

        Creates:
        - skills/{category}/{name}/main.py
        - skills/{category}/{name}/README.md
        - skills/{category}/{name}/.meta.json

        Args:
            code: Python code to save
            name: Skill name
            category: Skill category
            tags: Optional tags for discovery
        """
        logger.info(f"Saving skill: {category}/{name}")

        # Extract dependencies from code
        dependencies = self._extract_dependencies(code)

        # Create skill directory
        skill_dir = self.skills_dir / category / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Save main.py
        main_py_path = skill_dir / "main.py"
        main_py_path.write_text(code)

        # Extract docstring and generate README
        docstring = self._extract_docstring(code)
        readme_content = self._generate_readme(name, category, docstring, tags)
        readme_path = skill_dir / "README.md"
        readme_path.write_text(readme_content)

        # Generate and save metadata (with dependencies)
        metadata = self._generate_metadata(name, category, tags, dependencies)
        meta_path = skill_dir / ".meta.json"
        meta_path.write_text(json.dumps(metadata, indent=2))

        # Create __init__.py for imports
        init_path = skill_dir / "__init__.py"
        init_path.write_text(f'"""{docstring or name}"""\n\nfrom .main import *\n')

        logger.info(f"Skill saved: {skill_dir}")

        # Log telemetry
        if self.telemetry:
            code_lines = len(code.split('\n'))
            self.telemetry.log_skill_save(
                category=category,
                name=name,
                code_lines=code_lines,
                dependencies=dependencies,
            )

    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available skills.

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
        Get detailed info about a skill.

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

    def increment_usage(self, category: str, name: str) -> None:
        """
        Increment usage count for a skill.

        Args:
            category: Skill category
            name: Skill name
        """
        skill_dir = self.skills_dir / category / name
        meta_path = skill_dir / ".meta.json"

        if not meta_path.exists():
            logger.warning(f"Cannot increment usage: metadata not found for {category}/{name}")
            return

        try:
            metadata = json.loads(meta_path.read_text())
            metadata['usage_count'] = metadata.get('usage_count', 0) + 1
            metadata['last_used'] = datetime.now().isoformat()
            meta_path.write_text(json.dumps(metadata, indent=2))
        except Exception as e:
            logger.error(f"Failed to increment usage for {category}/{name}: {e}")

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

    def _generate_metadata(
        self,
        name: str,
        category: str,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate metadata for a skill.

        Args:
            name: Skill name
            category: Skill category
            tags: Optional tags
            dependencies: Optional MCP tool dependencies

        Returns:
            Metadata dict
        """
        return {
            "name": name,
            "category": category,
            "created": datetime.now().isoformat(),
            "usage_count": 0,
            "tags": tags or [],
            "dependencies": dependencies or [],
        }

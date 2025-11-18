"""Custom assertions for testing MCP Skill Framework."""

from pathlib import Path
from typing import Any, Dict, List


def assert_skill_directory_structure(skill_path: Path, skill_name: str) -> None:
    """
    Assert that a skill directory has the correct structure.

    Args:
        skill_path: Path to skill directory
        skill_name: Expected skill name
    """
    assert skill_path.exists(), f"Skill directory does not exist: {skill_path}"
    assert skill_path.is_dir(), f"Skill path is not a directory: {skill_path}"

    # Check required files
    main_py = skill_path / "main.py"
    readme_md = skill_path / "README.md"
    init_py = skill_path / "__init__.py"
    meta_json = skill_path / ".meta.json"

    assert main_py.exists(), f"Missing main.py in {skill_path}"
    assert readme_md.exists(), f"Missing README.md in {skill_path}"
    assert init_py.exists(), f"Missing __init__.py in {skill_path}"
    assert meta_json.exists(), f"Missing .meta.json in {skill_path}"


def assert_generated_api_structure(
    servers_dir: Path, server_name: str, tool_name: str
) -> None:
    """
    Assert that a generated API has the correct structure.

    Args:
        servers_dir: Path to servers directory
        server_name: Server name
        tool_name: Tool name
    """
    tool_path = servers_dir / server_name / tool_name
    assert tool_path.exists(), f"Tool directory does not exist: {tool_path}"
    assert tool_path.is_dir(), f"Tool path is not a directory: {tool_path}"

    # Check required files
    main_py = tool_path / "main.py"
    readme_md = tool_path / "README.md"
    init_py = tool_path / "__init__.py"

    assert main_py.exists(), f"Missing main.py in {tool_path}"
    assert readme_md.exists(), f"Missing README.md in {tool_path}"
    assert init_py.exists(), f"Missing __init__.py in {tool_path}"


def assert_function_signature(
    code: str, function_name: str, expected_params: List[str]
) -> None:
    """
    Assert that generated code has expected function signature.

    Args:
        code: Python code as string
        function_name: Expected function name
        expected_params: List of expected parameter names
    """
    assert f"def {function_name}(" in code, f"Function {function_name} not found"

    for param in expected_params:
        assert param in code, f"Parameter {param} not found in function signature"


def assert_imports_present(code: str, expected_imports: List[str]) -> None:
    """
    Assert that code contains expected imports.

    Args:
        code: Python code as string
        expected_imports: List of expected import statements
    """
    for import_stmt in expected_imports:
        assert import_stmt in code, f"Missing import: {import_stmt}"


def assert_skill_metadata(
    metadata: Dict[str, Any], expected_name: str, expected_category: str
) -> None:
    """
    Assert that skill metadata has expected values.

    Args:
        metadata: Metadata dict from .meta.json
        expected_name: Expected skill name
        expected_category: Expected category
    """
    assert metadata["name"] == expected_name, f"Expected name {expected_name}"
    assert (
        metadata["category"] == expected_category
    ), f"Expected category {expected_category}"
    assert "created_at" in metadata, "Missing created_at timestamp"
    assert "tags" in metadata, "Missing tags field"
    assert "dependencies" in metadata, "Missing dependencies field"


def assert_database_skill_record(
    record: Dict[str, Any], agent_name: str, skill_name: str
) -> None:
    """
    Assert that database skill record has required fields.

    Args:
        record: Skill record from database
        agent_name: Expected agent name
        skill_name: Expected skill name
    """
    assert record["agent_name"] == agent_name, f"Expected agent_name {agent_name}"
    assert record["skill_name"] == skill_name, f"Expected skill_name {skill_name}"
    assert "category" in record, "Missing category"
    assert "code" in record, "Missing code"
    assert "created_at" in record, "Missing created_at"
    assert "updated_at" in record, "Missing updated_at"

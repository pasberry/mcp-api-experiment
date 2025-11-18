"""
Tests for template rendering.

Tests the Jinja2 templates that generate Python code, README files,
and __init__.py files from MCP tool schemas.
"""

import pytest
from typing import List, Dict, Any

from mcp_skill_framework.templates import (
    generate_main_py,
    generate_readme_md,
    generate_init_py,
    _python_type_hint,
    _example_value,
)


class MockToolSchema:
    """Mock tool schema for testing."""

    def __init__(
        self,
        name: str,
        server: str,
        description: str,
        parameters: List[Dict[str, Any]],
    ):
        self.name = name
        self.server = server
        self.description = description
        self.parameters = parameters


class TestMainPyGeneration:
    """Test main.py template generation."""

    def test_generate_basic_function(self):
        """Test generating basic function with no parameters."""
        schema = MockToolSchema(
            name="test_tool",
            server="test_server",
            description="Test tool description",
            parameters=[],
        )

        result = generate_main_py(schema)

        # Check function naming pattern
        assert "def test_server_test_tool(" in result
        assert "Test tool description" in result
        assert "from mcp_skill_framework.runtime import mcp_call" in result
        assert 'server="test_server"' in result
        assert 'tool="test_tool"' in result

    def test_generate_function_with_required_parameters(self):
        """Test function with required parameters."""
        schema = MockToolSchema(
            name="read_file",
            server="filesystem",
            description="Read a file",
            parameters=[
                {
                    "name": "path",
                    "type": "string",
                    "required": True,
                    "description": "File path",
                }
            ],
        )

        result = generate_main_py(schema)

        # Check parameter in signature
        assert "def filesystem_read_file(path: str)" in result
        assert "path (string): File path" in result  # Template uses JSON type names
        assert "if path is not None:" in result
        assert "params['path'] = path" in result

    def test_generate_function_with_optional_parameters(self):
        """Test function with optional parameters."""
        schema = MockToolSchema(
            name="list_files",
            server="filesystem",
            description="List files",
            parameters=[
                {
                    "name": "limit",
                    "type": "integer",
                    "required": False,
                    "description": "Max number of files",
                }
            ],
        )

        result = generate_main_py(schema)

        # Check optional parameter with default
        assert "limit: int = None" in result
        assert "limit (integer, optional): Max number of files" in result  # Template uses JSON type names

    def test_generate_function_with_mixed_parameters(self):
        """Test function with both required and optional parameters."""
        schema = MockToolSchema(
            name="search",
            server="github",
            description="Search GitHub",
            parameters=[
                {"name": "query", "type": "string", "required": True, "description": "Search query"},
                {"name": "limit", "type": "integer", "required": False, "description": "Result limit"},
                {"name": "sort", "type": "string", "required": False, "description": "Sort order"},
            ],
        )

        result = generate_main_py(schema)

        # Check parameter order (required first, then optional)
        assert "query: str, limit: int = None, sort: str = None" in result
        assert "if query is not None:" in result
        assert "if limit is not None:" in result
        assert "if sort is not None:" in result

    def test_generate_function_with_default_values(self):
        """Test function with default values for optional params."""
        schema = MockToolSchema(
            name="fetch",
            server="http",
            description="HTTP fetch",
            parameters=[
                {
                    "name": "timeout",
                    "type": "number",
                    "required": False,
                    "default": 30.0,
                    "description": "Request timeout",
                }
            ],
        )

        result = generate_main_py(schema)

        # Check default value
        assert "timeout: float = 30.0" in result

    def test_parameter_type_mapping(self):
        """Test all JSON schema type mappings."""
        types = [
            ("string", "str"),
            ("integer", "int"),
            ("number", "float"),
            ("boolean", "bool"),
            ("array", "list"),
            ("object", "dict"),
        ]

        for json_type, python_type in types:
            schema = MockToolSchema(
                name="test",
                server="test",
                description="Test",
                parameters=[
                    {
                        "name": "param",
                        "type": json_type,
                        "required": True,
                        "description": f"{json_type} param",
                    }
                ],
            )

            result = generate_main_py(schema)
            assert f"param: {python_type}" in result

    def test_function_returns_any_type(self):
        """Test that functions return Any type by default."""
        schema = MockToolSchema(
            name="test", server="test", description="Test", parameters=[]
        )

        result = generate_main_py(schema)

        assert "-> Any:" in result
        assert "Any: Tool execution result" in result


class TestReadmeGeneration:
    """Test README.md template generation."""

    def test_generate_basic_readme(self):
        """Test generating basic README."""
        schema = MockToolSchema(
            name="test_tool",
            server="test_server",
            description="Test tool description",
            parameters=[],
        )

        result = generate_readme_md(schema)

        assert "# test_tool" in result
        assert "**Domain:** test_server" in result
        assert "Test tool description" in result
        assert "from servers.test_server.test_tool import test_server_test_tool" in result

    def test_readme_with_parameters(self):
        """Test README with parameters table."""
        schema = MockToolSchema(
            name="read_file",
            server="filesystem",
            description="Read a file",
            parameters=[
                {
                    "name": "path",
                    "type": "string",
                    "required": True,
                    "description": "File path",
                },
                {
                    "name": "encoding",
                    "type": "string",
                    "required": False,
                    "description": "File encoding",
                },
            ],
        )

        result = generate_readme_md(schema)

        # Check parameters table
        assert "## Parameters" in result
        assert "| Name | Type | Required | Description |" in result
        assert "| `path` | string | Yes | File path |" in result
        assert "| `encoding` | string | No | File encoding |" in result

    def test_readme_example_usage(self):
        """Test README example usage section."""
        schema = MockToolSchema(
            name="list_files",
            server="filesystem",
            description="List files",
            parameters=[
                {
                    "name": "directory",
                    "type": "string",
                    "required": True,
                    "description": "Directory path",
                }
            ],
        )

        result = generate_readme_md(schema)

        # Check example includes required parameters
        assert "## Example Usage" in result
        assert 'result = filesystem_list_files(directory="example")' in result

    def test_readme_tags(self):
        """Test README tags section."""
        schema = MockToolSchema(
            name="search",
            server="github",
            description="Search GitHub",
            parameters=[],
        )

        result = generate_readme_md(schema)

        assert "## Tags" in result
        assert "github, search" in result

    def test_readme_without_parameters(self):
        """Test README with no parameters."""
        schema = MockToolSchema(
            name="ping", server="test", description="Ping service", parameters=[]
        )

        result = generate_readme_md(schema)

        # Should not have parameters section
        # But should still have example usage
        assert "result = test_ping()" in result


class TestInitPyGeneration:
    """Test __init__.py template generation."""

    def test_generate_init_py(self):
        """Test basic __init__.py generation."""
        result = generate_init_py(
            description="Test module",
            server="test_server",
            tool_name="test_tool",
        )

        assert '"""Test module"""' in result
        assert "from .main import test_server_test_tool" in result
        assert "__all__ = ['test_server_test_tool']" in result

    def test_init_py_preserves_server_prefix(self):
        """Test that server prefix is maintained in exports."""
        result = generate_init_py(
            description="GitHub search",
            server="github",
            tool_name="search",
        )

        assert "from .main import github_search" in result
        assert "__all__ = ['github_search']" in result


class TestPythonTypeHint:
    """Test _python_type_hint() helper function."""

    def test_all_type_mappings(self):
        """Test all JSON schema to Python type mappings."""
        mappings = {
            "string": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
            "null": "None",
        }

        for json_type, python_type in mappings.items():
            assert _python_type_hint(json_type) == python_type

    def test_unknown_type_returns_any(self):
        """Test unknown types default to Any."""
        assert _python_type_hint("unknown") == "Any"
        assert _python_type_hint("custom") == "Any"
        assert _python_type_hint("") == "Any"


class TestExampleValue:
    """Test _example_value() helper function."""

    def test_all_example_values(self):
        """Test example value generation for all types."""
        examples = {
            "string": '"example"',
            "number": "0.0",
            "integer": "0",
            "boolean": "True",
            "array": "[]",
            "object": "{}",
        }

        for json_type, example in examples.items():
            assert _example_value(json_type) == example

    def test_unknown_type_returns_none(self):
        """Test unknown types return None."""
        assert _example_value("unknown") == "None"
        assert _example_value("custom") == "None"


class TestTemplateEdgeCases:
    """Test edge cases and special scenarios."""

    def test_function_with_special_characters_in_description(self):
        """Test handling of special characters in descriptions."""
        schema = MockToolSchema(
            name="test",
            server="test",
            description='Test with "quotes" and \'apostrophes\'',
            parameters=[],
        )

        result = generate_main_py(schema)

        # Should not break the generated code
        assert "def test_test(" in result

    def test_function_with_long_parameter_list(self):
        """Test function with many parameters."""
        params = [
            {"name": f"param{i}", "type": "string", "required": False, "description": f"Param {i}"}
            for i in range(10)
        ]

        schema = MockToolSchema(
            name="complex",
            server="test",
            description="Complex function",
            parameters=params,
        )

        result = generate_main_py(schema)

        # All parameters should be present
        for i in range(10):
            assert f"param{i}: str = None" in result
            assert f"if param{i} is not None:" in result
            assert f"params['param{i}'] = param{i}" in result

    def test_readme_with_missing_parameter_descriptions(self):
        """Test README when parameter descriptions are missing."""
        schema = MockToolSchema(
            name="test",
            server="test",
            description="Test",
            parameters=[
                {"name": "param", "type": "string", "required": True}
                # No description field
            ],
        )

        result = generate_readme_md(schema)

        # Should handle missing description gracefully
        assert "| `param` | string | Yes | N/A |" in result

    def test_empty_description(self):
        """Test handling of empty descriptions."""
        schema = MockToolSchema(
            name="test",
            server="test",
            description="",
            parameters=[],
        )

        result = generate_main_py(schema)
        readme = generate_readme_md(schema)

        # Should not break
        assert "def test_test(" in result
        assert "# test" in readme


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

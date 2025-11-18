"""
Templates for generating API files.
"""

from typing import Dict, Any, List
from jinja2 import Template


MAIN_PY_TEMPLATE = Template("""\"\"\"{{ description }}\"\"\"

from typing import Any
from mcp_skill_framework.runtime import mcp_call


def {{ server }}_{{ tool_name }}({{ parameters }}) -> {{ return_type }}:
    \"\"\"
    {{ description }}
    {% if param_docs %}

    Args:
    {%- for param in param_docs %}
        {{ param.name }} ({{ param.type }}{% if not param.required %}, optional{% endif %}): {{ param.description }}
    {%- endfor %}
    {% endif %}

    Returns:
        {{ return_type }}: Tool execution result
    \"\"\"
    params = {}
    {% for param in params_list -%}
    if {{ param.name }} is not None:
        params['{{ param.name }}'] = {{ param.name }}
    {% endfor %}

    return mcp_call(
        server="{{ server }}",
        tool="{{ tool }}",
        params=params
    )
""")


README_TEMPLATE = Template("""# {{ tool_name }}

**Domain:** {{ server_name }}
**Category:** API

## Description

{{ description }}
{% if parameters %}

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
{%- for param in parameters %}
| `{{ param.name }}` | {{ param.type }} | {{ 'Yes' if param.required else 'No' }} | {{ param.description or 'N/A' }} |
{%- endfor %}
{% endif %}

## Returns

`{{ return_type }}` - Tool execution result

## Example Usage

```python
from servers.{{ server_name }}.{{ tool_name }} import {{ server_name }}_{{ tool_name }}

result = {{ server_name }}_{{ tool_name }}({{ example_params }})
print(result)
```
{% if tags %}

## Tags

{{ tags | join(', ') }}
{% endif %}

## Generated

This API was auto-generated from the MCP server: `{{ server_name }}`
""")


INIT_PY_TEMPLATE = Template("""\"\"\"{{ description }}\"\"\"

from .main import {{ server }}_{{ tool_name }}

__all__ = ['{{ server }}_{{ tool_name }}']
""")


def generate_main_py(tool_schema: Any) -> str:
    """
    Generate main.py content from tool schema.

    Args:
        tool_schema: ToolSchema object

    Returns:
        Generated Python code
    """
    # Build parameter signature
    param_parts = []
    for param in tool_schema.parameters:
        param_type = _python_type_hint(param['type'])
        if param['required']:
            param_parts.append(f"{param['name']}: {param_type}")
        else:
            default = param.get('default', 'None')
            if default == 'None' or default is None:
                param_parts.append(f"{param['name']}: {param_type} = None")
            else:
                param_parts.append(f"{param['name']}: {param_type} = {repr(default)}")

    parameters = ", ".join(param_parts) if param_parts else ""

    # Return type (MCP doesn't provide this, so we default to Any)
    return_type = "Any"

    return MAIN_PY_TEMPLATE.render(
        server=tool_schema.server,
        tool=tool_schema.name,
        tool_name=tool_schema.name,
        description=tool_schema.description,
        parameters=parameters,
        param_docs=tool_schema.parameters,
        params_list=tool_schema.parameters,
        return_type=return_type,
    )


def generate_readme_md(tool_schema: Any) -> str:
    """
    Generate README.md content from tool schema.

    Args:
        tool_schema: ToolSchema object

    Returns:
        Generated markdown
    """
    # Build example parameters
    example_params = []
    for param in tool_schema.parameters:
        if param['required']:
            example_value = _example_value(param['type'])
            example_params.append(f"{param['name']}={example_value}")

    example_params_str = ", ".join(example_params) if example_params else ""

    # Extract tags
    tags = [tool_schema.server, tool_schema.name]

    return README_TEMPLATE.render(
        server_name=tool_schema.server,
        tool_name=tool_schema.name,
        description=tool_schema.description,
        parameters=tool_schema.parameters,
        return_type="Any",
        example_params=example_params_str,
        tags=tags,
    )


def generate_init_py(description: str, server: str, tool_name: str) -> str:
    """
    Generate __init__.py content.

    Args:
        description: Module description
        server: Server name
        tool_name: Name of the tool/function to export

    Returns:
        Generated Python code
    """
    return INIT_PY_TEMPLATE.render(description=description, server=server, tool_name=tool_name)


def _python_type_hint(json_type: str) -> str:
    """Convert JSON schema type to Python type hint."""
    type_mapping = {
        'string': 'str',
        'number': 'float',
        'integer': 'int',
        'boolean': 'bool',
        'array': 'list',
        'object': 'dict',
        'null': 'None',
    }
    return type_mapping.get(json_type, 'Any')


def _example_value(json_type: str) -> str:
    """Generate example value for a type."""
    examples = {
        'string': '"example"',
        'number': '0.0',
        'integer': '0',
        'boolean': 'True',
        'array': '[]',
        'object': '{}',
    }
    return examples.get(json_type, 'None')

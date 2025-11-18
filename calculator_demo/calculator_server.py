#!/usr/bin/env python3
"""
Simple Calculator MCP Server
Exposes basic arithmetic operations: add, subtract, multiply, divide
"""
import asyncio
import json
import sys
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent


# Create server instance
app = Server("calculator")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available calculator tools."""
    return [
        Tool(
            name="add",
            description="Add two numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="subtract",
            description="Subtract second number from first number",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="multiply",
            description="Multiply two numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="divide",
            description="Divide first number by second number",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "Numerator"
                    },
                    "b": {
                        "type": "number",
                        "description": "Denominator (cannot be zero)"
                    }
                },
                "required": ["a", "b"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute calculator operations."""

    # Extract arguments
    a = float(arguments.get("a", 0))
    b = float(arguments.get("b", 0))

    # Perform operation
    if name == "add":
        result = a + b
    elif name == "subtract":
        result = a - b
    elif name == "multiply":
        result = a * b
    elif name == "divide":
        if b == 0:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Division by zero"})
            )]
        result = a / b
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]

    # Return result
    return [TextContent(
        type="text",
        text=json.dumps({"result": result})
    )]


async def main():
    """Run the calculator MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

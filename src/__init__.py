"""
MCP Skill Framework

A framework for building agents with MCP through code execution and skill accumulation.
Converts MCP tools into domain-specific Python APIs that agents can compose into skills.
"""

from .framework import MCPApi
from .connector import MCPConnector
from .runtime import MCPRuntime, mcp_call
from .skill_manager import SkillManager
from .telemetry import TelemetryLogger
from .database import SkillsDatabase

__version__ = "0.1.0"

__all__ = [
    "MCPApi",
    "MCPConnector",
    "MCPRuntime",
    "mcp_call",
    "SkillManager",
    "TelemetryLogger",
    "SkillsDatabase",
]

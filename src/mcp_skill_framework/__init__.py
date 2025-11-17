"""
MCP Skill Framework

A framework for building agents with MCP through code execution and skill accumulation.
Converts MCP tools into domain-specific Python APIs that agents can compose into skills.
"""

from .framework import MCPApi
from .connector import MCPConnector
from .runtime import MCPRuntime, mcp_call
from .executor import CodeExecutor
from .skill_manager import SkillManager
from .checkpoint_manager import CheckpointManager
from .telemetry import TelemetryLogger

__version__ = "0.1.0"

__all__ = [
    "MCPApi",
    "MCPConnector",
    "MCPRuntime",
    "mcp_call",
    "CodeExecutor",
    "SkillManager",
    "CheckpointManager",
    "TelemetryLogger",
]

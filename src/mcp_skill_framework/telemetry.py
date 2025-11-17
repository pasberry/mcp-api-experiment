"""
Telemetry Logger - Structured logging with SQLite persistence.

Provides observability into:
- MCP tool calls (success/failure, duration, errors)
- Code execution (success/failure, duration, errors)
- Skill lifecycle (saves, executions, dependencies)
- API generation events
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TelemetryLogger:
    """
    Structured event logging with SQLite persistence.

    Stores all events in a single table with JSON payload,
    enabling rich queries while maintaining flexibility.
    """

    def __init__(self, db_path: Path):
        """
        Initialize telemetry logger.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create connection
        self.connection = sqlite3.connect(
            str(db_path),
            check_same_thread=False  # Allow multi-threaded access
        )
        self.connection.row_factory = sqlite3.Row  # Enable column access by name

        self._init_schema()
        logger.info(f"Telemetry logger initialized: {db_path}")

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.connection.cursor()

        # Create events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,

                -- Indexed fields for fast queries
                server TEXT,
                tool TEXT,
                skill_category TEXT,
                skill_name TEXT,
                success INTEGER,
                duration_ms INTEGER,
                error_type TEXT
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON events(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON events(event_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_server_tool
            ON events(server, tool)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill
            ON events(skill_category, skill_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_success
            ON events(success)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_type
            ON events(error_type)
        """)

        self.connection.commit()

    def _log_event(
        self,
        level: str,
        event_type: str,
        data: Dict[str, Any],
        server: Optional[str] = None,
        tool: Optional[str] = None,
        skill_category: Optional[str] = None,
        skill_name: Optional[str] = None,
        success: Optional[bool] = None,
        duration_ms: Optional[float] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Log an event to the database.

        Args:
            level: Log level (INFO, WARN, ERROR, DEBUG)
            event_type: Type of event (mcp_call, code_execution, etc.)
            data: Full event data as dict
            server: Server name (for MCP events)
            tool: Tool name (for MCP events)
            skill_category: Skill category (for skill events)
            skill_name: Skill name (for skill events)
            success: Whether operation succeeded
            duration_ms: Operation duration in milliseconds
            error_type: Error type if failed
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'

        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO events (
                timestamp, level, event_type, data,
                server, tool, skill_category, skill_name,
                success, duration_ms, error_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            level,
            event_type,
            json.dumps(data),
            server,
            tool,
            skill_category,
            skill_name,
            1 if success is True else (0 if success is False else None),
            duration_ms,
            error_type,
        ))

        self.connection.commit()

        # Also log to console
        log_msg = f"[{event_type}] "
        if server and tool:
            log_msg += f"{server}.{tool} "
        elif skill_category and skill_name:
            log_msg += f"{skill_category}/{skill_name} "

        if success is not None:
            log_msg += "✓" if success else "✗"
        if duration_ms is not None:
            log_msg += f" ({duration_ms:.0f}ms)"
        if error_type:
            log_msg += f" - {error_type}"

        if level == "ERROR":
            logger.error(log_msg)
        elif level == "WARN":
            logger.warning(log_msg)
        elif level == "DEBUG":
            logger.debug(log_msg)
        else:
            logger.info(log_msg)

    def log_mcp_call(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        success: bool,
        duration_ms: float,
        result: Optional[Any] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """
        Log an MCP tool call.

        Args:
            server: Server name
            tool: Tool name
            params: Tool parameters
            success: Whether call succeeded
            duration_ms: Call duration in milliseconds
            result: Result if successful
            error: Exception if failed
        """
        data = {
            "params": params,
        }

        if success and result is not None:
            # Capture result metadata
            data["result_type"] = type(result).__name__
            if isinstance(result, (list, dict)):
                data["result_count"] = len(result)

        error_type = None
        if error:
            error_type = type(error).__name__
            data["error_message"] = str(error)

        self._log_event(
            level="ERROR" if not success else "INFO",
            event_type="mcp_call",
            data=data,
            server=server,
            tool=tool,
            success=success,
            duration_ms=duration_ms,
            error_type=error_type,
        )

    def log_code_execution(
        self,
        mode: str,
        code_lines: int,
        success: bool,
        duration_ms: float,
        return_value: Optional[Any] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log code execution.

        Args:
            mode: Execution mode (docker/subprocess)
            code_lines: Number of lines of code
            success: Whether execution succeeded
            duration_ms: Execution duration in milliseconds
            return_value: Return value if successful
            error: Error details if failed
        """
        data = {
            "mode": mode,
            "code_lines": code_lines,
        }

        if success and return_value is not None:
            data["return_value_type"] = type(return_value).__name__

        error_type = None
        if error:
            error_type = error.get("type")
            data["error"] = error

        self._log_event(
            level="ERROR" if not success else "INFO",
            event_type="code_execution",
            data=data,
            success=success,
            duration_ms=duration_ms,
            error_type=error_type,
        )

    def log_skill_execution(
        self,
        category: str,
        name: str,
        success: bool,
        duration_ms: float,
        mcp_calls_made: int = 0,
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log skill execution.

        Args:
            category: Skill category
            name: Skill name
            success: Whether execution succeeded
            duration_ms: Execution duration in milliseconds
            mcp_calls_made: Number of MCP calls made during execution
            error: Error details if failed
        """
        data = {
            "mcp_calls_made": mcp_calls_made,
        }

        error_type = None
        if error:
            error_type = error.get("type")
            data["error"] = error

        self._log_event(
            level="ERROR" if not success else "INFO",
            event_type="skill_execution",
            data=data,
            skill_category=category,
            skill_name=name,
            success=success,
            duration_ms=duration_ms,
            error_type=error_type,
        )

    def log_skill_save(
        self,
        category: str,
        name: str,
        code_lines: int,
        dependencies: List[Dict[str, str]],
    ) -> None:
        """
        Log skill save event.

        Args:
            category: Skill category
            name: Skill name
            code_lines: Number of lines of code
            dependencies: List of MCP tool dependencies
        """
        data = {
            "code_lines": code_lines,
            "dependencies": dependencies,
        }

        self._log_event(
            level="INFO",
            event_type="skill_save",
            data=data,
            skill_category=category,
            skill_name=name,
            success=True,
        )

    def log_api_generation(
        self,
        server: str,
        tools_count: int,
        duration_ms: float,
        tools_added: Optional[List[str]] = None,
        tools_removed: Optional[List[str]] = None,
        tools_modified: Optional[List[str]] = None,
    ) -> None:
        """
        Log API generation event.

        Args:
            server: Server name
            tools_count: Total number of tools
            duration_ms: Generation duration in milliseconds
            tools_added: List of added tool names
            tools_removed: List of removed tool names
            tools_modified: List of modified tool names
        """
        data = {
            "tools_count": tools_count,
        }

        if tools_added:
            data["tools_added"] = tools_added
        if tools_removed:
            data["tools_removed"] = tools_removed
        if tools_modified:
            data["tools_modified"] = tools_modified

        level = "WARN" if (tools_removed or tools_modified) else "INFO"

        self._log_event(
            level=level,
            event_type="api_generation",
            data=data,
            server=server,
            success=True,
            duration_ms=duration_ms,
        )

    def log_server_connection(
        self,
        server: str,
        success: bool,
        duration_ms: float,
        error: Optional[Exception] = None,
    ) -> None:
        """
        Log server connection event.

        Args:
            server: Server name
            success: Whether connection succeeded
            duration_ms: Connection duration in milliseconds
            error: Exception if failed
        """
        data = {}

        error_type = None
        if error:
            error_type = type(error).__name__
            data["error_message"] = str(error)

        self._log_event(
            level="ERROR" if not success else "INFO",
            event_type="server_connection",
            data=data,
            server=server,
            success=success,
            duration_ms=duration_ms,
            error_type=error_type,
        )

    def get_tool_metrics(self) -> List[Dict[str, Any]]:
        """
        Get aggregated metrics for MCP tool calls.

        Returns:
            List of tool metrics with success/failure counts
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT
                server,
                tool,
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                ROUND(AVG(duration_ms), 2) as avg_duration_ms,
                ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct
            FROM events
            WHERE event_type = 'mcp_call'
            GROUP BY server, tool
            ORDER BY total_calls DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_skill_metrics(self) -> List[Dict[str, Any]]:
        """
        Get aggregated metrics for skill executions.

        Returns:
            List of skill metrics with success/failure counts
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT
                skill_category,
                skill_name,
                COUNT(*) as total_executions,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_executions,
                ROUND(AVG(duration_ms), 2) as avg_duration_ms,
                ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct
            FROM events
            WHERE event_type = 'skill_execution'
            GROUP BY skill_category, skill_name
            ORDER BY total_executions DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_error_patterns(self) -> List[Dict[str, Any]]:
        """
        Get common error patterns.

        Returns:
            List of error types with occurrence counts
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT
                error_type,
                event_type,
                COUNT(*) as occurrences,
                MAX(timestamp) as last_seen
            FROM events
            WHERE success = 0 AND error_type IS NOT NULL
            GROUP BY error_type, event_type
            ORDER BY occurrences DESC
            LIMIT 20
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_health_snapshot(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get system health snapshot for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            Health metrics by event type
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT
                event_type,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct,
                ROUND(AVG(duration_ms), 2) as avg_duration_ms
            FROM events
            WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                AND event_type IN ('mcp_call', 'code_execution', 'skill_execution')
            GROUP BY event_type
        """, (hours,))

        results = [dict(row) for row in cursor.fetchall()]

        return {
            "hours": hours,
            "metrics": results
        }

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Telemetry logger closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

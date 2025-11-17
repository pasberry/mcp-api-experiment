# SQL Queries for Telemetry Database

This directory contains useful SQL queries for analyzing telemetry data collected by the MCP Skill Framework.

## Database Location

By default, the telemetry database is located at:
```
.mcp_telemetry/telemetry.db
```

## Running Queries

### Using SQLite CLI
```bash
sqlite3 .mcp_telemetry/telemetry.db < sql/tool_metrics.sql
```

### Using Python
```python
import sqlite3

conn = sqlite3.connect('.mcp_telemetry/telemetry.db')
cursor = conn.cursor()

# Read and execute query
with open('sql/tool_metrics.sql') as f:
    query = f.read()

cursor.execute(query)
for row in cursor.fetchall():
    print(row)
```

### Using the Telemetry API
```python
from mcp_skill_framework.telemetry import TelemetryLogger

telemetry = TelemetryLogger(Path('.mcp_telemetry/telemetry.db'))

# Get pre-built metrics
tool_metrics = telemetry.get_tool_metrics()
skill_metrics = telemetry.get_skill_metrics()
error_patterns = telemetry.get_error_patterns()
health = telemetry.get_health_snapshot(hours=24)
```

## Available Queries

### tool_metrics.sql
**Purpose:** Success/failure counts and performance metrics for MCP tools

**Use cases:**
- Identify most-used tools
- Find tools with high failure rates
- Monitor tool performance

**Output columns:**
- `server`, `tool`: Tool identifier
- `total_calls`: Total number of calls
- `successful_calls`, `failed_calls`: Breakdown
- `success_rate_pct`: Success percentage
- `avg_duration_ms`: Average execution time

---

### skill_metrics.sql
**Purpose:** Success/failure counts and performance metrics for skills

**Use cases:**
- Identify most-used skills
- Find problematic skills
- Monitor skill performance

**Output columns:**
- `skill_category`, `skill_name`: Skill identifier
- `total_executions`: Total number of executions
- `successful_executions`, `failed_executions`: Breakdown
- `success_rate_pct`: Success percentage
- `avg_duration_ms`: Average execution time

---

### error_patterns.sql
**Purpose:** Most common errors in the system

**Use cases:**
- Identify recurring problems
- Prioritize bug fixes
- Understand failure modes

**Output columns:**
- `error_type`: Type of error (e.g., ZeroDivisionError)
- `event_type`: Where error occurred (mcp_call, code_execution, etc.)
- `occurrences`: Number of times seen
- `last_seen`: Most recent occurrence

---

### health_snapshot.sql
**Purpose:** Overall system health for last 24 hours

**Use cases:**
- Daily health check
- Monitor system reliability
- Detect degradation

**Output columns:**
- `event_type`: Type of operation
- `total`, `successful`, `failed`: Counts
- `success_rate_pct`: Success percentage
- `avg_duration_ms`: Average performance

---

### tool_usage_over_time.sql
**Purpose:** Hourly breakdown for a specific tool

**Use cases:**
- Identify usage patterns
- Detect when failures started
- Monitor specific tool health

**Configuration:** Edit query to change server/tool name

**Output columns:**
- `hour`: Timestamp (hourly buckets)
- `calls`, `successful`, `failed`: Call counts
- `avg_duration_ms`: Average performance

---

### recent_failures.sql
**Purpose:** Last 50 failed operations with details

**Use cases:**
- Debugging recent issues
- Investigating user reports
- Error analysis

**Output columns:**
- `timestamp`: When failure occurred
- `event_type`, `error_type`: What failed
- `mcp_tool`, `skill`: Context
- `duration_ms`: How long it took
- `data`: Full event JSON

---

### skill_dependencies.sql
**Purpose:** Which skills use which MCP tools

**Use cases:**
- Impact analysis for tool deprecation
- Find skills using specific tools
- Understand dependency graph

**Output columns:**
- `skill_category`, `skill_name`: Skill identifier
- `created`: When skill was saved
- `dependencies`: JSON array of MCP tools used
- `code_lines`: Size of skill code

## Custom Queries

The database schema is designed for flexibility. You can write custom queries using:

### Events Table Schema
```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  timestamp TEXT,
  level TEXT,              -- INFO, WARN, ERROR, DEBUG
  event_type TEXT,         -- mcp_call, code_execution, skill_execution, etc.
  data TEXT,               -- Full JSON event data

  -- Indexed fields for fast queries
  server TEXT,
  tool TEXT,
  skill_category TEXT,
  skill_name TEXT,
  success INTEGER,         -- 1 = success, 0 = failure
  duration_ms INTEGER,
  error_type TEXT
);
```

### Example Custom Query
```sql
-- Find slowest MCP calls in last hour
SELECT
  server || '.' || tool as mcp_tool,
  duration_ms,
  timestamp,
  data
FROM events
WHERE event_type = 'mcp_call'
  AND timestamp >= datetime('now', '-1 hour')
ORDER BY duration_ms DESC
LIMIT 10;
```

## Event Types

- **mcp_call**: MCP tool invocation
- **code_execution**: Agent code execution
- **skill_execution**: Skill execution
- **skill_save**: Skill saved to disk
- **api_generation**: APIs generated from MCP server
- **server_connection**: MCP server connection attempt

## Tips

1. **Performance**: Queries on indexed fields (timestamp, server, tool, skill_category, skill_name, success) are fast
2. **JSON data**: Use `json_extract(data, '$.field')` to query JSON fields
3. **Time ranges**: SQLite datetime functions like `datetime('now', '-24 hours')` are useful
4. **Aggregations**: Use GROUP BY with time buckets for trend analysis

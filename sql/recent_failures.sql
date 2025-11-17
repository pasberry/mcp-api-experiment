-- Recent Failures - Last 50 failed operations
--
-- Shows recent failures across all event types with details:
-- - Timestamp
-- - Event type (mcp_call, code_execution, skill_execution)
-- - Error type
-- - Full event data (JSON)
-- - Server/tool or skill context
--
-- Useful for debugging and investigating issues
-- Ordered by most recent first

SELECT
  timestamp,
  event_type,
  error_type,
  server || '.' || tool as mcp_tool,
  skill_category || '/' || skill_name as skill,
  duration_ms,
  data
FROM events
WHERE success = 0
ORDER BY timestamp DESC
LIMIT 50;

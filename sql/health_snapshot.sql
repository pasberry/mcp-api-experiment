-- Health Snapshot - System health for last 24 hours
--
-- Shows aggregated metrics for different event types:
-- - mcp_call: MCP tool invocations
-- - code_execution: Agent code executions
-- - skill_execution: Skill runs
--
-- For each event type shows:
-- - Total events
-- - Successful vs failed
-- - Success rate percentage
-- - Average execution time
--
-- Useful for monitoring overall system health

SELECT
  event_type,
  COUNT(*) as total,
  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
  SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
  ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct,
  ROUND(AVG(duration_ms), 2) as avg_duration_ms
FROM events
WHERE timestamp >= datetime('now', '-24 hours')
  AND event_type IN ('mcp_call', 'code_execution', 'skill_execution')
GROUP BY event_type;

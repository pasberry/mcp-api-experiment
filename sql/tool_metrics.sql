-- Tool Metrics - Success/Failure counts and performance for MCP tools
--
-- Shows aggregated statistics for each MCP tool including:
-- - Total number of calls
-- - Successful vs failed calls
-- - Success rate percentage
-- - Average execution time
--
-- Ordered by total calls descending to show most-used tools first

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
ORDER BY total_calls DESC;

-- Tool Usage Over Time - Hourly breakdown for a specific tool
--
-- Shows call volume and success/failure counts per hour
-- for a specific MCP tool over the last 24 hours
--
-- Useful for:
-- - Identifying usage patterns
-- - Detecting when failures started
-- - Monitoring tool health over time
--
-- USAGE: Replace 'google-drive' and 'list_files' with your tool

SELECT
  strftime('%Y-%m-%d %H:00', timestamp) as hour,
  COUNT(*) as calls,
  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
  SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
  ROUND(AVG(duration_ms), 2) as avg_duration_ms
FROM events
WHERE event_type = 'mcp_call'
  AND server = 'google-drive'
  AND tool = 'list_files'
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;

-- Skill Metrics - Success/Failure counts and performance for skills
--
-- Shows aggregated statistics for each skill including:
-- - Total number of executions
-- - Successful vs failed executions
-- - Success rate percentage
-- - Average execution time
--
-- Ordered by total executions descending to show most-used skills first

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
ORDER BY total_executions DESC;

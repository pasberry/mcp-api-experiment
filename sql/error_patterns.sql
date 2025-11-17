-- Error Patterns - Most common errors in the system
--
-- Shows:
-- - Error type (e.g., ZeroDivisionError, NameError)
-- - Event type where error occurred (mcp_call, code_execution, etc.)
-- - Number of occurrences
-- - Last time this error was seen
--
-- Ordered by occurrence count descending
-- Limited to top 20 most common errors

SELECT
  error_type,
  event_type,
  COUNT(*) as occurrences,
  MAX(timestamp) as last_seen
FROM events
WHERE success = 0 AND error_type IS NOT NULL
GROUP BY error_type, event_type
ORDER BY occurrences DESC
LIMIT 20;

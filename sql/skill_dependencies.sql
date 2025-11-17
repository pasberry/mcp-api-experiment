-- Skill Dependencies - Which skills use which MCP tools
--
-- Extracts dependency information from skill_save events
-- Shows which skills depend on which MCP tools
--
-- Useful for:
-- - Understanding skill dependencies
-- - Impact analysis when tools are deprecated
-- - Finding skills that use a specific tool
--
-- Note: Dependencies are extracted from skill code at save time

SELECT
  skill_category,
  skill_name,
  timestamp as created,
  json_extract(data, '$.dependencies') as dependencies,
  json_extract(data, '$.code_lines') as code_lines
FROM events
WHERE event_type = 'skill_save'
ORDER BY timestamp DESC;

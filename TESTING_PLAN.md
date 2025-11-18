# Testing Plan - MCP Skill Framework

## Current Test Coverage

**Status**: 13 tests passing (tests/test_basic.py)

**Covered**:
- ✅ Database initialization and CRUD operations
- ✅ Skill manager filesystem operations
- ✅ Dependency extraction from code
- ✅ Hydration from database (happy path)
- ✅ MCPApi initialization and basic operations
- ✅ Multi-agent database isolation

## Testing Gaps

### Priority 1: Critical (Must Have)

#### 1. CLI Code Generation Tests
**File**: `tests/test_cli.py` (missing)
**Lines**: ~200 estimated
**Why Critical**: CLI is the primary developer workflow entry point

**Required Tests**:
- [ ] `test_cli_generate_from_config_file()` - End-to-end CLI execution
- [ ] `test_cli_validates_config_format()` - JSON validation
- [ ] `test_cli_handles_missing_config_file()` - Error handling
- [ ] `test_cli_creates_correct_directory_structure()` - Verify output
- [ ] `test_cli_output_flag()` - Custom output directory
- [ ] `test_cli_quiet_flag()` - Suppress output
- [ ] `test_cli_invalid_server_config()` - Skip invalid entries
- [ ] `test_generate_servers_function()` - Test Python API directly

**Test Data Needed**:
```json
// tests/fixtures/valid-config.json
{
  "servers": [
    {"name": "test_server", "command": "echo test"}
  ]
}

// tests/fixtures/invalid-config.json
{
  "servers": "not-a-list"
}
```

#### 2. Runtime Execution Tests
**File**: `tests/test_runtime.py` (missing)
**Lines**: ~250 estimated
**Why Critical**: Core execution path for agent operations

**Required Tests**:
- [ ] `test_mcp_call_routes_to_correct_server()` - Routing logic
- [ ] `test_mcp_call_without_runtime_raises_error()` - Error when not initialized
- [ ] `test_runtime_register_servers()` - Server registration
- [ ] `test_runtime_handles_async_calls()` - Event loop handling
- [ ] `test_runtime_extracts_result_content()` - MCP response parsing
- [ ] `test_runtime_handles_tool_error()` - Error responses from MCP
- [ ] `test_runtime_logs_telemetry()` - Verify telemetry calls
- [ ] `test_runtime_concurrent_calls()` - Multiple simultaneous calls
- [ ] `test_runtime_singleton_pattern()` - Global instance behavior

**Mocking Required**:
- Mock `ClientSession` from mcp library
- Mock MCP server responses (success and error cases)
- Mock telemetry logging

#### 3. Integration with Real MCP Servers
**File**: `tests/test_integration_mcp.py` (missing)
**Lines**: ~300 estimated
**Why Critical**: No real-world validation currently exists

**Required Tests**:
- [ ] `test_connect_to_filesystem_server()` - Actual MCP server
- [ ] `test_introspect_filesystem_tools()` - list_tools() call
- [ ] `test_execute_real_filesystem_read()` - Real tool execution
- [ ] `test_handle_server_subprocess_crash()` - Process failure
- [ ] `test_handle_server_timeout()` - Slow/hanging server
- [ ] `test_handle_invalid_mcp_response()` - Malformed responses
- [ ] `test_multiple_servers_simultaneously()` - Concurrent servers
- [ ] `test_server_cleanup_on_shutdown()` - Process cleanup

**Infrastructure Required**:
- Install `@modelcontextprotocol/server-filesystem` in CI
- Temporary directories for test files
- Process cleanup fixtures

#### 4. End-to-End Workflow Tests
**File**: `tests/test_e2e_workflow.py` (missing)
**Lines**: ~400 estimated
**Why Critical**: Validates complete use cases

**Required Tests**:
- [ ] `test_complete_developer_workflow()` - Config → Generate → Import
- [ ] `test_complete_agent_workflow()` - Hydrate → Discover → Execute → Save
- [ ] `test_restart_and_hydrate_scenario()` - Persistence across restarts
- [ ] `test_skill_persists_across_sessions()` - Database as source of truth
- [ ] `test_add_new_mcp_server_workflow()` - Incremental updates
- [ ] `test_agent_discovers_and_uses_existing_skill()` - Skill reuse
- [ ] `test_two_agents_same_database()` - Multi-agent isolation

**Scenarios to Cover**:
```python
# Scenario 1: Developer generates, agent uses
1. Generate code from config
2. Import generated function
3. Execute function
4. Verify result

# Scenario 2: Agent saves skill, restarts, uses skill
1. Agent saves skill to DB
2. Simulate restart (clear filesystem)
3. Hydrate from DB
4. Import and use hydrated skill
```

---

### Priority 2: Important (Should Have)

#### 5. Discovery Tools Tests
**File**: `tests/test_discovery_tools.py` (missing)
**Lines**: ~200 estimated
**Why Important**: Agent framework integration depends on these

**Required Tests**:
- [ ] `test_list_available_skills_formatting()` - Output format
- [ ] `test_list_available_skills_empty_db()` - Handle no skills
- [ ] `test_list_available_skills_filters_by_category()` - Category filtering
- [ ] `test_get_skill_categories_empty_db()` - Empty state
- [ ] `test_get_skill_categories_multiple()` - Multiple categories
- [ ] `test_create_skill_validates_name()` - Name validation
- [ ] `test_create_skill_validates_category()` - Category validation
- [ ] `test_create_skill_validates_code()` - Code validation

**Files to Test**:
- `examples/agent_discovery_pattern.py` functions

#### 6. Template Rendering Tests
**File**: `tests/test_templates.py` (missing)
**Lines**: ~250 estimated
**Why Important**: Generated code quality depends on templates

**Required Tests**:
- [ ] `test_main_py_template_renders()` - Basic rendering
- [ ] `test_function_naming_pattern()` - {server}_{tool} format
- [ ] `test_parameter_type_mapping()` - JSON schema → Python types
- [ ] `test_optional_vs_required_parameters()` - Optional handling
- [ ] `test_readme_template_includes_examples()` - Documentation
- [ ] `test_readme_template_includes_parameters()` - Parameter docs
- [ ] `test_init_py_exports_correct_function()` - __all__ list
- [ ] `test_template_handles_complex_types()` - Arrays, objects
- [ ] `test_template_escapes_special_chars()` - String escaping

**Test Data**:
```python
# Mock tool schema
{
  "name": "test_tool",
  "description": "Test tool",
  "inputSchema": {
    "type": "object",
    "properties": {
      "required_param": {"type": "string"},
      "optional_param": {"type": "number"}
    },
    "required": ["required_param"]
  }
}
```

#### 7. Multi-Agent Scenarios
**File**: `tests/test_multi_agent.py` (missing)
**Lines**: ~200 estimated
**Why Important**: Multi-agent support is a key feature

**Required Tests**:
- [ ] `test_two_agents_shared_database()` - Shared DB
- [ ] `test_agent_only_sees_own_skills()` - Isolation
- [ ] `test_concurrent_skill_creation_different_agents()` - Concurrency
- [ ] `test_same_skill_name_different_agents()` - Name collision
- [ ] `test_statistics_per_agent()` - Stats isolation
- [ ] `test_hydration_concurrent_agents()` - Concurrent hydration
- [ ] `test_database_locking()` - SQLite concurrency

#### 8. Error Handling Tests
**File**: `tests/test_error_handling.py` (missing)
**Lines**: ~200 estimated
**Why Important**: Production robustness

**Required Tests**:
- [ ] `test_invalid_skill_name_characters()` - Name validation
- [ ] `test_invalid_category_name()` - Category validation
- [ ] `test_skill_code_with_syntax_error()` - Code validation
- [ ] `test_database_connection_failure()` - DB errors
- [ ] `test_database_disk_full()` - Storage errors
- [ ] `test_filesystem_permission_denied()` - Permission errors
- [ ] `test_missing_mcp_server_executable()` - Server launch failure
- [ ] `test_mcp_call_missing_required_param()` - Parameter validation
- [ ] `test_corrupted_meta_json()` - Malformed metadata

---

### Priority 3: Nice to Have (Could Have)

#### 9. Hydration Edge Cases
**File**: `tests/test_hydration_edge_cases.py` (missing)
**Lines**: ~150 estimated

**Required Tests**:
- [ ] `test_hydration_with_none_metadata()` - Already fixed, add test
- [ ] `test_hydration_with_none_dependencies()` - Already fixed, add test
- [ ] `test_hydration_with_empty_database()` - No skills
- [ ] `test_hydration_clears_existing_skills()` - Cleanup behavior
- [ ] `test_hydration_partial_failure()` - Some skills fail
- [ ] `test_hydration_creates_directory_structure()` - Dir creation

#### 10. Dependency Extraction Edge Cases
**File**: `tests/test_dependency_extraction.py` (missing)
**Lines**: ~100 estimated

**Required Tests**:
- [ ] `test_extract_duplicate_dependencies()` - Deduplication
- [ ] `test_extract_nested_mcp_calls()` - Loops/nested calls
- [ ] `test_ignore_mcp_call_in_strings()` - False positives
- [ ] `test_ignore_mcp_call_in_comments()` - Comments
- [ ] `test_extract_multiline_mcp_call()` - Multiline calls

#### 11. Telemetry Tests
**File**: `tests/test_telemetry.py` (missing)
**Lines**: ~150 estimated

**Required Tests**:
- [ ] `test_telemetry_logs_mcp_calls()` - Call logging
- [ ] `test_telemetry_logs_errors()` - Error logging
- [ ] `test_telemetry_disabled()` - Disable functionality
- [ ] `test_telemetry_query_by_server()` - Query filtering
- [ ] `test_telemetry_query_by_timerange()` - Time filtering

---

## Test Metrics Summary

| Priority | Test Files | Est. Tests | Est. Lines | Status |
|----------|-----------|-----------|-----------|---------|
| **Current** | 1 | 13 | 363 | ✅ Passing |
| **Priority 1** | 4 | ~50 | ~1,150 | ❌ Missing |
| **Priority 2** | 4 | ~35 | ~850 | ❌ Missing |
| **Priority 3** | 3 | ~20 | ~400 | ❌ Missing |
| **TOTAL** | **12** | **~118** | **~2,763** | **11% Coverage** |

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create `tests/test_runtime.py` - Core execution path
- [ ] Create `tests/test_cli.py` - Developer workflow
- [ ] Add fixtures for test data (configs, mock servers)

### Phase 2: Integration (Week 2)
- [ ] Create `tests/test_integration_mcp.py` - Real servers
- [ ] Create `tests/test_e2e_workflow.py` - Complete scenarios
- [ ] Set up CI infrastructure (install MCP servers)

### Phase 3: Robustness (Week 3)
- [ ] Create `tests/test_discovery_tools.py` - Agent integration
- [ ] Create `tests/test_templates.py` - Code quality
- [ ] Create `tests/test_error_handling.py` - Error cases

### Phase 4: Edge Cases (Week 4)
- [ ] Create `tests/test_multi_agent.py` - Concurrency
- [ ] Create `tests/test_hydration_edge_cases.py` - Edge cases
- [ ] Create `tests/test_dependency_extraction.py` - Parsing edge cases
- [ ] Create `tests/test_telemetry.py` - Observability

---

## Test Infrastructure Needs

### CI/CD Requirements
```yaml
# .github/workflows/test.yml additions needed:
- Install Node.js (for npx)
- Install @modelcontextprotocol/server-filesystem
- Set up temporary directories for integration tests
- Install pytest-timeout for slow tests
- Install pytest-xdist for parallel execution
```

### Test Fixtures Needed
```
tests/
├── fixtures/
│   ├── configs/
│   │   ├── valid-single-server.json
│   │   ├── valid-multi-server.json
│   │   ├── invalid-format.json
│   │   └── empty-servers.json
│   ├── skills/
│   │   ├── simple_skill.py
│   │   ├── skill_with_deps.py
│   │   └── invalid_skill.py
│   └── databases/
│       ├── prepopulated.db
│       └── corrupted.db
├── mocks/
│   ├── mock_mcp_server.py
│   └── mock_client_session.py
└── helpers/
    ├── assertions.py
    └── test_utils.py
```

### pytest Configuration Additions
```ini
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: Integration tests with real MCP servers",
    "e2e: End-to-end workflow tests",
    "slow: Tests that take >5 seconds",
    "requires_node: Tests that require Node.js/npx",
]
timeout = 30  # Default timeout for tests
```

---

## Coverage Goals

### Current Coverage
- **Lines**: ~11% (363 / 3,200 total lines)
- **Branches**: Unknown (no coverage reports)
- **Integration**: 0%

### Target Coverage (After All Phases)
- **Lines**: >80%
- **Branches**: >70%
- **Integration**: Key workflows covered
- **Critical Paths**: 100% (runtime, database, CLI)

---

## Test Execution Strategy

### Local Development
```bash
# Quick unit tests (no integration)
pytest tests/ -m "not integration and not e2e"

# All tests including integration
pytest tests/

# Specific priority
pytest tests/test_runtime.py tests/test_cli.py
```

### CI Pipeline
```bash
# Stage 1: Fast unit tests
pytest tests/ -m "not integration and not slow" --maxfail=3

# Stage 2: Integration tests
pytest tests/ -m "integration" --timeout=60

# Stage 3: E2E tests
pytest tests/ -m "e2e" --timeout=120

# Coverage report
pytest tests/ --cov=mcp_skill_framework --cov-report=html
```

---

## Notes

- Priority 1 tests are **blocking** - must be completed before production use
- Priority 2 tests are **important** - complete before beta release
- Priority 3 tests are **polish** - complete before v1.0
- Integration tests require Node.js environment
- Multi-agent tests may need database process isolation
- Template tests should validate generated code can actually run

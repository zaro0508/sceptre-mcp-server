# Tasks

## Task 1: Project Scaffolding and Package Structure

- [x] 1. Set up the source directory and package files
  - [x] 1.1 Create `src/sceptre_mcp_server/__init__.py` (empty package init)
  - [x] 1.2 Create `src/sceptre_mcp_server/server.py` with FastMCP server instance and `main()` entry point
  - [x] 1.3 Create `tests/` directory with `tests/__init__.py` and `tests/test_server.py` skeleton

## Task 2: Implement Helper Functions

- [x] 2. Implement core helper functions in `server.py`
  - [x] 2.1 Implement `_validate_project_dir(sceptre_project_dir: str) -> None` that checks directory exists and contains `config/` subdirectory
  - [x] 2.2 Implement `_run_sceptre_command(sceptre_project_dir, command_path, command, *args, ignore_dependencies=False) -> dict` that creates SceptreContext, SceptrePlan, and executes the command
  - [x] 2.3 Implement `_format_response(result: dict, command: str) -> str` that formats sceptre response dicts into human-readable text, handling StackStatus enums and datetime objects

## Task 3: Implement Stack Lifecycle Tools

- [x] 3. Implement stack lifecycle MCP tools
  - [x] 3.1 Implement `create_stack(sceptre_project_dir, stack_path) -> str` tool
  - [x] 3.2 Implement `update_stack(sceptre_project_dir, stack_path) -> str` tool
  - [x] 3.3 Implement `delete_stack(sceptre_project_dir, stack_path) -> str` tool
  - [x] 3.4 Implement `launch_stack(sceptre_project_dir, stack_path) -> str` tool

## Task 4: Implement Query Tools

- [x] 4. Implement stack query MCP tools
  - [x] 4.1 Implement `get_stack_status(sceptre_project_dir, stack_path) -> str` tool
  - [x] 4.2 Implement `describe_stack(sceptre_project_dir, stack_path) -> str` tool
  - [x] 4.3 Implement `describe_stack_outputs(sceptre_project_dir, stack_path) -> str` tool
  - [x] 4.4 Implement `describe_stack_resources(sceptre_project_dir, stack_path) -> str` tool
  - [x] 4.5 Implement `describe_stack_events(sceptre_project_dir, stack_path) -> str` tool

## Task 5: Implement Template Tools

- [ ] 5. Implement template MCP tools
  - [ ] 5.1 Implement `generate_template(sceptre_project_dir, stack_path) -> str` tool
  - [ ] 5.2 Implement `validate_template(sceptre_project_dir, stack_path) -> str` tool


## Task 6: Implement Diff and Drift Tools

- [ ] 6. Implement diff and drift MCP tools
  - [ ] 6.1 Implement `diff_stack(sceptre_project_dir, stack_path, diff_type="deepdiff") -> str` tool that creates the appropriate StackDiffer and formats output via DiffWriter
  - [ ] 6.2 Implement `drift_detect(sceptre_project_dir, stack_path) -> str` tool
  - [ ] 6.3 Implement `drift_show(sceptre_project_dir, stack_path, drifted_only=False) -> str` tool

## Task 7: Implement Discovery and Configuration Tools

- [ ] 7. Implement discovery and configuration MCP tools
  - [ ] 7.1 Implement `list_stacks(sceptre_project_dir, stack_path="") -> str` tool that iterates plan.graph to collect stack names and external names
  - [ ] 7.2 Implement `dump_config(sceptre_project_dir, stack_path) -> str` tool

## Task 8: Implement Change Set Tools

- [ ] 8. Implement change set MCP tools
  - [ ] 8.1 Implement `create_change_set(sceptre_project_dir, stack_path, change_set_name) -> str` tool
  - [ ] 8.2 Implement `describe_change_set(sceptre_project_dir, stack_path, change_set_name) -> str` tool
  - [ ] 8.3 Implement `list_change_sets(sceptre_project_dir, stack_path) -> str` tool
  - [ ] 8.4 Implement `execute_change_set(sceptre_project_dir, stack_path, change_set_name) -> str` tool
  - [ ] 8.5 Implement `delete_change_set(sceptre_project_dir, stack_path, change_set_name) -> str` tool

## Task 9: Write Unit Tests

- [ ] 9. Write unit tests for the server
  - [ ] 9.1 Write tests for `_validate_project_dir` (valid dir, missing dir, missing config/)
  - [ ] 9.2 Write tests for `_format_response` (normal responses, StackStatus enums, datetime objects, error cases)
  - [ ] 9.3 Write tests for stack lifecycle tools (create, update, delete, launch) with mocked SceptrePlan
  - [ ] 9.4 Write tests for query tools (status, describe, outputs, resources, events) with mocked SceptrePlan
  - [ ] 9.5 Write tests for error handling (SceptreException, generic Exception)

## Task 10: Update README

- [x] 10. Update README.md with installation instructions, MCP client configuration examples, and tool reference documentation

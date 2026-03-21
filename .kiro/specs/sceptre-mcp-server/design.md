# Design Document

## Overview

The sceptre-mcp-server is a Python MCP server built on the FastMCP framework that exposes Sceptre's CloudFormation management capabilities as MCP tools. AI agents connect to the server and invoke tools to manage AWS CloudFormation stacks through Sceptre's Python API.

## Architecture

```
┌─────────────┐       MCP Protocol        ┌──────────────────────┐
│  AI Agent    │ ◄──────────────────────►  │  sceptre-mcp-server  │
│ (Kiro/Claude)│                           │  (FastMCP)           │
└─────────────┘                           ├──────────────────────┤
                                          │  Tool Functions      │
                                          │  ┌────────────────┐  │
                                          │  │ create_stack   │  │
                                          │  │ update_stack   │  │
                                          │  │ delete_stack   │  │
                                          │  │ launch_stack   │  │
                                          │  │ get_status     │  │
                                          │  │ describe_stack │  │
                                          │  │ ...            │  │
                                          │  └────────────────┘  │
                                          ├──────────────────────┤
                                          │  Helpers             │
                                          │  ┌────────────────┐  │
                                          │  │ _run_sceptre   │  │
                                          │  │ _format_resp   │  │
                                          │  │ _validate_proj │  │
                                          │  └────────────────┘  │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  Sceptre Library     │
                                          │  ┌────────────────┐  │
                                          │  │ SceptreContext  │  │
                                          │  │ SceptrePlan    │  │
                                          │  │ StackActions   │  │
                                          │  └────────────────┘  │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  AWS CloudFormation  │
                                          └──────────────────────┘
```

## Components

### 1. Server Module (`src/sceptre_mcp_server/server.py`)

Single module containing the FastMCP server instance, all tool functions, and helper utilities.

```python
from fastmcp import FastMCP

mcp = FastMCP("sceptre-mcp-server")
```

### 2. Helper Functions

#### `_run_sceptre_command`

Central helper that creates a `SceptreContext`, builds a `SceptrePlan`, and executes a command. All tool functions delegate to this helper for the core sceptre interaction.

```python
def _run_sceptre_command(
    sceptre_project_dir: str,
    command_path: str,
    command: str,
    *args,
    ignore_dependencies: bool = False,
) -> dict:
```

**Flow:**
1. Validate `sceptre_project_dir` exists and contains a `config/` directory
2. Create `SceptreContext(project_path=sceptre_project_dir, command_path=command_path, ignore_dependencies=ignore_dependencies)`
3. Create `SceptrePlan(context)`
4. Call `getattr(plan, command)(*args)` to execute the command
5. Return the raw result dict `{stack_external_name: response}`

#### `_format_response`

Formats the raw sceptre response dict into a human-readable string for the AI agent.

```python
def _format_response(result: dict, command: str) -> str:
```

**Behavior:**
- Iterates over `{stack_name: response}` pairs
- Converts non-serializable objects (e.g., `StackStatus` enums, `datetime`) to strings
- Returns a formatted text block with stack name and result

#### `_validate_project_dir`

Validates that a directory is a valid Sceptre project.

```python
def _validate_project_dir(sceptre_project_dir: str) -> None:
```

**Checks:**
- Directory exists
- Contains a `config/` subdirectory
- Raises `ValueError` with descriptive message on failure

### 3. Entry Point

```python
def main():
    mcp.run()
```

Registered in `pyproject.toml` as `sceptre-mcp-server = "sceptre_mcp_server.server:main"` under `[tool.poetry.scripts]`.

## Tool Specifications

All tools follow a consistent pattern:
- Accept `sceptre_project_dir: str` as the first parameter
- Accept `stack_path: str` for stack-specific operations
- Return `str` (formatted text response)
- Catch all exceptions and return error messages

### Stack Lifecycle Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `create_stack` | `sceptre_project_dir`, `stack_path` | `plan.create()` | 2, 19, 20 |
| `update_stack` | `sceptre_project_dir`, `stack_path` | `plan.update()` | 3, 19, 20 |
| `delete_stack` | `sceptre_project_dir`, `stack_path` | `plan.delete()` | 4, 19, 20 |
| `launch_stack` | `sceptre_project_dir`, `stack_path` | `plan.launch()` | 5, 19, 20 |

### Query Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `get_stack_status` | `sceptre_project_dir`, `stack_path` | `plan.get_status()` | 6, 19, 20 |
| `describe_stack` | `sceptre_project_dir`, `stack_path` | `plan.describe()` | 7, 19, 20 |
| `describe_stack_outputs` | `sceptre_project_dir`, `stack_path` | `plan.describe_outputs()` | 8, 19, 20 |
| `describe_stack_resources` | `sceptre_project_dir`, `stack_path` | `plan.describe_resources()` | 9, 19, 20 |
| `describe_stack_events` | `sceptre_project_dir`, `stack_path` | `plan.describe_events()` | 10, 19, 20 |

### Template Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `generate_template` | `sceptre_project_dir`, `stack_path` | `plan.generate()` | 11, 19, 20 |
| `validate_template` | `sceptre_project_dir`, `stack_path` | `plan.validate()` | 12, 19, 20 |

### Diff and Drift Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `diff_stack` | `sceptre_project_dir`, `stack_path`, `diff_type: str = "deepdiff"` | `plan.diff(stack_differ)` | 13, 19, 20 |
| `drift_detect` | `sceptre_project_dir`, `stack_path` | `plan.drift_detect()` | 14, 19, 20 |
| `drift_show` | `sceptre_project_dir`, `stack_path`, `drifted_only: bool = False` | `plan.drift_show(drifted)` | 15, 19, 20 |

**`diff_stack` implementation note:** The `diff` command requires a `StackDiffer` instance. The tool creates either a `DeepDiffStackDiffer` or `DifflibStackDiffer` based on the `diff_type` parameter, then formats the `StackDiff` result using a `DiffWriter` to produce text output.

### Discovery Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `list_stacks` | `sceptre_project_dir`, `stack_path: str = ""` | `plan.graph` iteration | 16, 19, 20 |

**`list_stacks` implementation note:** Creates a `SceptreContext` with the given `stack_path` (or root `""` for all stacks), builds a `SceptrePlan`, resolves it, then iterates `plan.graph` to collect `{stack.name: stack.external_name}` pairs.

### Change Set Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `create_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | `plan.create_change_set(name)` | 17, 19, 20 |
| `describe_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | `plan.describe_change_set(name)` | 17, 19, 20 |
| `list_change_sets` | `sceptre_project_dir`, `stack_path` | `plan.list_change_sets()` | 17, 19, 20 |
| `execute_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | `plan.execute_change_set(name)` | 17, 19, 20 |
| `delete_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | `plan.delete_change_set(name)` | 17, 19, 20 |

### Configuration Tools

| Tool | Parameters | Sceptre Command | Reqs |
|------|-----------|----------------|------|
| `dump_config` | `sceptre_project_dir`, `stack_path` | `plan.dump_config()` | 18, 19, 20 |

## Error Handling Strategy

All tool functions use a common try/except pattern:

```python
@mcp.tool()
def some_tool(sceptre_project_dir: str, stack_path: str) -> str:
    """Tool description."""
    try:
        _validate_project_dir(sceptre_project_dir)
        result = _run_sceptre_command(sceptre_project_dir, stack_path, "command_name")
        return _format_response(result, "command_name")
    except SceptreException as e:
        return f"Sceptre error for '{stack_path}': {type(e).__name__}: {e}"
    except Exception as e:
        return f"Unexpected error for '{stack_path}': {type(e).__name__}: {e}"
```

**Exception hierarchy handled:**
- `SceptreException` (base) — all sceptre-specific errors including:
  - `StackDoesNotExistError`
  - `InvalidSceptreDirectoryError`
  - `InvalidConfigFileError`
  - `ConfigFileNotFoundError`
  - `ProtectedStackError`
  - `CannotUpdateFailedStackError`
- `botocore.exceptions.ClientError` — AWS API errors
- `Exception` — catch-all for unexpected errors

All error responses include:
- The `stack_path` for context
- The exception type name
- The exception message

## Response Format

Tool responses are plain text strings. For successful operations:

```
Stack: my-project/dev/vpc
Status: CREATE_COMPLETE
```

For query operations returning structured data (describe, outputs, resources, events):

```
Stack: my-project/dev/vpc
{json-formatted response data}
```

For errors:

```
Sceptre error for 'dev/vpc.yaml': StackDoesNotExistError: Stack does not exist
```

## File Structure

```
sceptre-mcp-server/
├── src/
│   └── sceptre_mcp_server/
│       ├── __init__.py          # Empty package init
│       └── server.py            # FastMCP server, all tools, helpers
├── tests/
│   └── test_server.py           # Unit tests
├── pyproject.toml               # Package config, dependencies, entry point
└── README.md                    # Usage documentation
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastmcp` | `>=0.2.0` | MCP server framework |
| `sceptre` | `>=4.0.0` | CloudFormation management library |

Build system: `poetry-core` (configured in `[build-system]`)

## Traceability Matrix

| Requirement | Tool(s) | Design Section |
|-------------|---------|----------------|
| Req 1: Server Init | `main()`, `FastMCP("sceptre-mcp-server")` | Components §1, §3 |
| Req 2: Create | `create_stack` | Stack Lifecycle Tools |
| Req 3: Update | `update_stack` | Stack Lifecycle Tools |
| Req 4: Delete | `delete_stack` | Stack Lifecycle Tools |
| Req 5: Launch | `launch_stack` | Stack Lifecycle Tools |
| Req 6: Status | `get_stack_status` | Query Tools |
| Req 7: Describe | `describe_stack` | Query Tools |
| Req 8: Outputs | `describe_stack_outputs` | Query Tools |
| Req 9: Resources | `describe_stack_resources` | Query Tools |
| Req 10: Events | `describe_stack_events` | Query Tools |
| Req 11: Generate | `generate_template` | Template Tools |
| Req 12: Validate | `validate_template` | Template Tools |
| Req 13: Diff | `diff_stack` | Diff and Drift Tools |
| Req 14: Drift Detect | `drift_detect` | Diff and Drift Tools |
| Req 15: Drift Show | `drift_show` | Diff and Drift Tools |
| Req 16: List | `list_stacks` | Discovery Tools |
| Req 17: Change Sets | `create_change_set`, `describe_change_set`, `list_change_sets`, `execute_change_set`, `delete_change_set` | Change Set Tools |
| Req 18: Dump Config | `dump_config` | Configuration Tools |
| Req 19: Parameters | All tools | Tool Specifications (common pattern) |
| Req 20: Error Handling | All tools | Error Handling Strategy |
| Req 21: Distribution | `pyproject.toml` (poetry-core), `main()` | Components §3, Dependencies |

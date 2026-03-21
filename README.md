# sceptre-mcp-server

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that exposes [Sceptre](https://github.com/Sceptre/sceptre) CloudFormation management operations as tools for AI agents.

## What it does

AI agents (Claude, Kiro, etc.) can connect to this server and manage AWS CloudFormation stacks through Sceptre's Python API. The server exposes 22 tools covering the full stack lifecycle:

- **Stack lifecycle** — create, update, delete, launch
- **Querying** — status, describe, outputs, resources, events
- **Templates** — generate, validate
- **Diff & drift** — diff against deployed state, detect and show drift
- **Change sets** — create, describe, list, execute, delete
- **Discovery** — list stacks, dump resolved config

## Requirements

- Python 3.10+
- A configured [Sceptre project](https://docs.sceptre-project.org/) with `config/` and `templates/` directories

## Installation

```bash
pip install sceptre-mcp-server
```

Or run directly without installing:

```bash
uvx sceptre-mcp-server
```

## MCP Client Configuration

### Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "sceptre": {
      "command": "uvx",
      "args": ["sceptre-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sceptre": {
      "command": "uvx",
      "args": ["sceptre-mcp-server"]
    }
  }
}
```

## Tools Reference

Every tool requires a `sceptre_project_dir` parameter pointing to your Sceptre project root. Stack-specific tools also require a `stack_path` relative to the `config/` directory.

### Stack Lifecycle

| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_stack` | `sceptre_project_dir`, `stack_path` | Create a new CloudFormation stack |
| `update_stack` | `sceptre_project_dir`, `stack_path` | Update an existing stack |
| `delete_stack` | `sceptre_project_dir`, `stack_path` | Delete a stack |
| `launch_stack` | `sceptre_project_dir`, `stack_path` | Create or update a stack as needed |

### Querying

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_stack_status` | `sceptre_project_dir`, `stack_path` | Get current stack status |
| `describe_stack` | `sceptre_project_dir`, `stack_path` | Get full stack details |
| `describe_stack_outputs` | `sceptre_project_dir`, `stack_path` | Get stack output values |
| `describe_stack_resources` | `sceptre_project_dir`, `stack_path` | List stack resources |
| `describe_stack_events` | `sceptre_project_dir`, `stack_path` | Get stack event history |

### Templates

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_template` | `sceptre_project_dir`, `stack_path` | Render the CloudFormation template |
| `validate_template` | `sceptre_project_dir`, `stack_path` | Validate template with CloudFormation |

### Diff & Drift

| Tool | Parameters | Description |
|------|-----------|-------------|
| `diff_stack` | `sceptre_project_dir`, `stack_path`, `diff_type` | Diff local template vs deployed (deepdiff or difflib) |
| `drift_detect` | `sceptre_project_dir`, `stack_path` | Detect configuration drift |
| `drift_show` | `sceptre_project_dir`, `stack_path`, `drifted_only` | Show drift details |

### Change Sets

| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | Create a change set |
| `describe_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | Describe a change set |
| `list_change_sets` | `sceptre_project_dir`, `stack_path` | List all change sets |
| `execute_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | Execute a change set |
| `delete_change_set` | `sceptre_project_dir`, `stack_path`, `change_set_name` | Delete a change set |

### Discovery & Configuration

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_stacks` | `sceptre_project_dir`, `stack_path` (optional) | List stacks in the project |
| `dump_config` | `sceptre_project_dir`, `stack_path` | Dump resolved stack configuration |

## Example Usage

Once connected, an AI agent can invoke tools like:

```
> List all stacks in my project at /home/user/infra

Calls: list_stacks(sceptre_project_dir="/home/user/infra")

> What's the status of the dev VPC stack?

Calls: get_stack_status(sceptre_project_dir="/home/user/infra", stack_path="dev/vpc.yaml")

> Show me what would change if I deploy the prod API stack

Calls: diff_stack(sceptre_project_dir="/home/user/infra", stack_path="prod/api.yaml")
```

## AWS Configuration

Sceptre uses the standard AWS credential chain. To specify a profile or region, pass environment variables through your MCP client config:

```json
{
  "mcpServers": {
    "sceptre": {
      "command": "uvx",
      "args": ["sceptre-mcp-server"],
      "env": {
        "AWS_PROFILE": "my-profile",
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```

## Project Specs

Design documentation for this project lives in the `.kiro/specs/sceptre-mcp-server/` directory:

- [Requirements](.kiro/specs/sceptre-mcp-server/requirements.md) — 22 functional requirements covering server init, stack lifecycle, querying, templates, diff/drift, change sets, config dump, parameter conventions, error handling, AWS configuration, and distribution
- [Design](.kiro/specs/sceptre-mcp-server/design.md) — Architecture, component design, tool specifications, error handling strategy, response format, and traceability matrix
- [Tasks](.kiro/specs/sceptre-mcp-server/tasks.md) — Implementation task breakdown with sub-tasks

## Development

```bash
# Clone and install dependencies
git clone <repo-url>
cd sceptre-mcp-server
poetry install

# Run tests
poetry run pytest -q
```

## License

Apache-2.0

# Requirements Document

## Introduction

The sceptre-mcp-server exposes Sceptre's CloudFormation management capabilities as MCP (Model Context Protocol) tools. AI agents can invoke these tools to create, update, delete, query, and manage AWS CloudFormation stacks through Sceptre's Python API. The server is built on the FastMCP Python framework and is installable via pip or uvx.

## Glossary

- **MCP_Server**: The FastMCP-based server process that registers and serves Sceptre operations as MCP tools
- **MCP_Tool**: A single callable function exposed by the MCP_Server that performs a specific Sceptre operation
- **AI_Agent**: An MCP client (e.g., Claude, Kiro) that invokes MCP_Tools via the Model Context Protocol
- **Sceptre_Project**: A directory containing a `config/` folder with stack configuration files and a `templates/` folder with CloudFormation templates, as defined by Sceptre conventions
- **Stack_Path**: A relative path identifying a stack or stack group within a Sceptre_Project config directory (e.g., `dev/vpc.yaml`)
- **SceptreContext**: The Sceptre object that holds project path, command path, and execution options for a plan
- **SceptrePlan**: The Sceptre object that resolves a command against a SceptreContext and executes it across stacks
- **Tool_Response**: A structured string or JSON object returned by an MCP_Tool to the AI_Agent

## Requirements

### Requirement 1: MCP Server Initialization

**User Story:** As a developer, I want to start the sceptre-mcp-server so that AI agents can connect and invoke Sceptre operations.

#### Acceptance Criteria

1. WHEN the MCP_Server process is started, THE MCP_Server SHALL register all Sceptre MCP_Tools and accept incoming MCP connections
2. THE MCP_Server SHALL be launchable via the `sceptre-mcp-server` console script entry point defined in pyproject.toml
3. THE MCP_Server SHALL be launchable via `uvx sceptre-mcp-server` without prior installation

### Requirement 2: Stack Creation

**User Story:** As an AI agent, I want to create a CloudFormation stack so that I can provision infrastructure on behalf of the user.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the create stack MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL create a SceptreContext and execute the `create` command via SceptrePlan
2. WHEN the create operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack name and its resulting status
3. IF the Sceptre_Project directory does not exist or is invalid, THEN THE MCP_Tool SHALL return a Tool_Response containing a descriptive error message
4. IF the Stack_Path does not correspond to a valid stack configuration, THEN THE MCP_Tool SHALL return a Tool_Response containing a descriptive error message
5. IF the create operation fails due to a CloudFormation error, THEN THE MCP_Tool SHALL return a Tool_Response containing the error details from Sceptre

### Requirement 3: Stack Update

**User Story:** As an AI agent, I want to update an existing CloudFormation stack so that I can apply infrastructure changes.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the update stack MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `update` command via SceptrePlan
2. WHEN the update operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack name and its resulting status
3. IF the update operation fails due to a Sceptre or CloudFormation error, THEN THE MCP_Tool SHALL return a Tool_Response containing the error details

### Requirement 4: Stack Deletion

**User Story:** As an AI agent, I want to delete a CloudFormation stack so that I can tear down infrastructure.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the delete stack MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `delete` command via SceptrePlan
2. WHEN the delete operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack name and its resulting status
3. IF the delete operation fails due to a Sceptre or CloudFormation error, THEN THE MCP_Tool SHALL return a Tool_Response containing the error details

### Requirement 5: Stack Launch

**User Story:** As an AI agent, I want to launch a stack (create or update as appropriate) so that I can ensure infrastructure is in the desired state.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the launch stack MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `launch` command via SceptrePlan
2. THE launch MCP_Tool SHALL create the stack if the stack does not exist, or update the stack if the stack already exists
3. WHEN the launch operation completes, THE MCP_Tool SHALL return a Tool_Response containing the stack name and its resulting status
4. IF the launch operation fails, THEN THE MCP_Tool SHALL return a Tool_Response containing the error details

### Requirement 6: Stack Status Query

**User Story:** As an AI agent, I want to query the status of a CloudFormation stack so that I can report its current state.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the get status MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `get_status` command via SceptrePlan
2. WHEN the status query succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack name and its current CloudFormation status
3. IF the stack does not exist in CloudFormation, THEN THE MCP_Tool SHALL return a Tool_Response indicating the stack does not exist

### Requirement 7: Stack Describe

**User Story:** As an AI agent, I want to describe a CloudFormation stack so that I can retrieve its full details.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the describe stack MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `describe` command via SceptrePlan
2. WHEN the describe operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack description details from CloudFormation

### Requirement 8: Stack Outputs Query

**User Story:** As an AI agent, I want to retrieve the outputs of a CloudFormation stack so that I can use output values in subsequent operations.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the describe outputs MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `describe_outputs` command via SceptrePlan
2. WHEN the outputs query succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack output keys and values

### Requirement 9: Stack Resources Query

**User Story:** As an AI agent, I want to list the resources in a CloudFormation stack so that I can understand what infrastructure is provisioned.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the describe resources MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `describe_resources` command via SceptrePlan
2. WHEN the resources query succeeds, THE MCP_Tool SHALL return a Tool_Response containing the logical and physical resource identifiers, types, and statuses

### Requirement 10: Stack Events Query

**User Story:** As an AI agent, I want to retrieve the events for a CloudFormation stack so that I can diagnose deployment issues.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the describe events MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `describe_events` command via SceptrePlan
2. WHEN the events query succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack event records

### Requirement 11: Template Generation

**User Story:** As an AI agent, I want to generate a CloudFormation template from a Sceptre stack configuration so that I can inspect the template before deployment.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the generate template MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `generate` command via SceptrePlan
2. WHEN the generate operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the rendered CloudFormation template body

### Requirement 12: Template Validation

**User Story:** As an AI agent, I want to validate a CloudFormation template so that I can verify correctness before deployment.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the validate template MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `validate` command via SceptrePlan
2. WHEN the validation succeeds, THE MCP_Tool SHALL return a Tool_Response indicating the template is valid
3. IF the template validation fails, THEN THE MCP_Tool SHALL return a Tool_Response containing the validation error details from CloudFormation

### Requirement 13: Stack Diff

**User Story:** As an AI agent, I want to diff a stack's local template against its deployed state so that I can preview changes before applying them.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the diff MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `diff` command via SceptrePlan
2. WHEN the diff operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the differences between the local and deployed stack configurations
3. IF the stack has not been deployed, THEN THE MCP_Tool SHALL return a Tool_Response indicating the stack is new and showing the full template as additions

### Requirement 14: Stack Drift Detection

**User Story:** As an AI agent, I want to detect configuration drift on a deployed stack so that I can identify out-of-band changes.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the drift detect MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `drift_detect` command via SceptrePlan
2. WHEN the drift detection completes, THE MCP_Tool SHALL return a Tool_Response containing the drift detection status for the stack

### Requirement 15: Stack Drift Show

**User Story:** As an AI agent, I want to view the drift details for a stack so that I can understand what resources have drifted.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the drift show MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `drift_show` command via SceptrePlan
2. THE drift show MCP_Tool SHALL accept an optional parameter to filter results to only drifted resources
3. WHEN the drift show operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the resource-level drift details

### Requirement 16: Stack List and Discovery

**User Story:** As an AI agent, I want to list available stacks in a Sceptre project so that I can discover what infrastructure is managed.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the list stacks MCP_Tool with a valid Sceptre_Project directory, THE MCP_Server SHALL scan the project config directory and return all available Stack_Paths
2. THE list stacks MCP_Tool SHALL accept an optional Stack_Path parameter to scope listing to a specific stack group
3. WHEN the listing succeeds, THE MCP_Tool SHALL return a Tool_Response containing the stack paths and their associated configuration file names

### Requirement 17: Change Set Management

**User Story:** As an AI agent, I want to create, describe, list, execute, and delete change sets so that I can preview and control stack updates.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the create change set MCP_Tool with a valid Sceptre_Project directory, Stack_Path, and change set name, THE MCP_Server SHALL execute the `create_change_set` command via SceptrePlan
2. WHEN the AI_Agent invokes the describe change set MCP_Tool with a valid Sceptre_Project directory, Stack_Path, and change set name, THE MCP_Server SHALL execute the `describe_change_set` command via SceptrePlan
3. WHEN the AI_Agent invokes the list change sets MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `list_change_sets` command via SceptrePlan
4. WHEN the AI_Agent invokes the execute change set MCP_Tool with a valid Sceptre_Project directory, Stack_Path, and change set name, THE MCP_Server SHALL execute the `execute_change_set` command via SceptrePlan
5. WHEN the AI_Agent invokes the delete change set MCP_Tool with a valid Sceptre_Project directory, Stack_Path, and change set name, THE MCP_Server SHALL execute the `delete_change_set` command via SceptrePlan
6. IF any change set operation fails, THEN THE MCP_Tool SHALL return a Tool_Response containing the error details

### Requirement 18: Dump Stack Configuration

**User Story:** As an AI agent, I want to dump the resolved Sceptre configuration for a stack so that I can inspect the effective settings.

#### Acceptance Criteria

1. WHEN the AI_Agent invokes the dump config MCP_Tool with a valid Sceptre_Project directory and Stack_Path, THE MCP_Server SHALL execute the `dump_config` command via SceptrePlan
2. WHEN the dump config operation succeeds, THE MCP_Tool SHALL return a Tool_Response containing the fully resolved stack configuration

### Requirement 19: Common Tool Parameter Handling

**User Story:** As a developer, I want all MCP tools to follow a consistent parameter convention so that the AI agent can invoke tools predictably.

#### Acceptance Criteria

1. THE MCP_Server SHALL require a `sceptre_project_dir` string parameter on every MCP_Tool that identifies the absolute or relative path to the Sceptre_Project directory
2. THE MCP_Server SHALL require a `stack_path` string parameter on every MCP_Tool that operates on a specific stack, identifying the Stack_Path within the Sceptre_Project config directory
3. IF the `sceptre_project_dir` parameter points to a directory that does not contain a valid Sceptre_Project structure, THEN THE MCP_Tool SHALL return a Tool_Response containing a descriptive error message
4. IF the `stack_path` parameter does not correspond to a valid stack configuration file, THEN THE MCP_Tool SHALL return a Tool_Response containing a descriptive error message

### Requirement 20: Error Handling and Response Format

**User Story:** As an AI agent, I want clear, structured error messages so that I can understand failures and suggest corrective actions to the user.

#### Acceptance Criteria

1. IF a Sceptre exception occurs during MCP_Tool execution, THEN THE MCP_Server SHALL catch the exception and return a Tool_Response containing the exception type and message
2. IF an unexpected error occurs during MCP_Tool execution, THEN THE MCP_Server SHALL catch the error and return a Tool_Response containing a generic error message and the exception details
3. THE MCP_Server SHALL return Tool_Responses as text content that the AI_Agent can parse and present to the user
4. THE MCP_Server SHALL include the stack name or Stack_Path in every Tool_Response for context

### Requirement 21: Installation and Distribution

**User Story:** As a developer, I want to install the sceptre-mcp-server via pip so that I can configure it as an MCP server in my AI agent client.

#### Acceptance Criteria

1. THE sceptre-mcp-server package SHALL be installable via `pip install sceptre-mcp-server` (from a built wheel) or via `poetry install` for development
2. THE sceptre-mcp-server package SHALL declare `fastmcp>=0.2.0` and `sceptre>=4.0.0` as runtime dependencies in `[tool.poetry.dependencies]`
3. THE sceptre-mcp-server package SHALL use the `src/sceptre_mcp_server/` source layout as defined in pyproject.toml with `poetry-core` as the build backend
4. WHEN installed, THE sceptre-mcp-server package SHALL provide a `sceptre-mcp-server` console script entry point via `[tool.poetry.scripts]`

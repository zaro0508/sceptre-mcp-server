"""sceptre-mcp-server: MCP server exposing Sceptre CloudFormation operations as tools."""

import io
import json
import os
from datetime import datetime
from enum import Enum

from fastmcp import FastMCP

from sceptre.context import SceptreContext
from sceptre.diffing.diff_writer import DeepDiffWriter, DiffLibWriter
from sceptre.diffing.stack_differ import DeepDiffStackDiffer, DifflibStackDiffer
from sceptre.exceptions import SceptreException
from sceptre.plan.plan import SceptrePlan

mcp = FastMCP("sceptre-mcp-server")


def _validate_project_dir(sceptre_project_dir: str) -> None:
    """Validate that the given path is a valid Sceptre project directory.

    Checks that the directory exists and contains a config/ subdirectory.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :raises ValueError: If the directory does not exist or lacks config/.
    """
    if not os.path.isdir(sceptre_project_dir):
        raise ValueError(
            f"Sceptre project directory does not exist: {sceptre_project_dir}"
        )
    config_path = os.path.join(sceptre_project_dir, "config")
    if not os.path.isdir(config_path):
        raise ValueError(
            f"Sceptre project directory does not contain a config/ subdirectory: {sceptre_project_dir}"
        )


def _build_plan(
    sceptre_project_dir: str,
    command_path: str,
    ignore_dependencies: bool = False,
) -> SceptrePlan:
    """Validate the project directory and build a SceptrePlan.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param command_path: Relative path to the stack or stack group within config/.
    :param ignore_dependencies: If True, skip dependency resolution.
    :returns: A ready-to-use SceptrePlan instance.
    """
    _validate_project_dir(sceptre_project_dir)
    context = SceptreContext(
        project_path=sceptre_project_dir,
        command_path=command_path,
        ignore_dependencies=ignore_dependencies,
    )
    return SceptrePlan(context)


def _run_sceptre_command(
    sceptre_project_dir: str,
    command_path: str,
    command: str,
    *args,
    ignore_dependencies: bool = False,
) -> dict:
    """Create a SceptreContext and SceptrePlan, then execute the given command.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param command_path: Relative path to the stack or stack group within config/.
    :param command: Name of the SceptrePlan method to invoke (e.g. "create", "delete").
    :param args: Additional positional arguments forwarded to the plan command.
    :param ignore_dependencies: If True, skip dependency resolution.
    :returns: The raw result dict {stack_external_name: response}.
    """
    plan = _build_plan(sceptre_project_dir, command_path, ignore_dependencies)
    plan_command = getattr(plan, command)
    return plan_command(*args)


def _make_serializable(obj):
    """Recursively convert non-serializable objects to strings.

    Handles Enum members, datetime objects, and other non-JSON-serializable types
    that commonly appear in Sceptre responses.
    """
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    return obj


def _format_response(result: dict, command: str) -> str:
    """Format a Sceptre response dict into human-readable text.

    :param result: The raw result dict from SceptrePlan, typically
        {stack_external_name: response_value}.
    :param command: The command name, used in the output header.
    :returns: A formatted text string suitable for returning to the AI agent.
    """
    lines = []
    for stack_name, response in result.items():
        stack_label = str(stack_name)
        lines.append(f"Stack: {stack_label}")
        lines.append(f"Command: {command}")
        serializable = _make_serializable(response)
        if isinstance(serializable, str):
            lines.append(f"Status: {serializable}")
        else:
            lines.append(json.dumps(serializable, indent=2, default=str))
        lines.append("")
    return "\n".join(lines).strip()


def _safe_execute(stack_path: str, fn, *args, **kwargs) -> str:
    """Run *fn* with standard Sceptre error handling.

    :param stack_path: Used only for error messages.
    :param fn: Callable that performs the actual work and returns a str.
    :param args: Positional arguments forwarded to *fn*.
    :param kwargs: Keyword arguments forwarded to *fn*.
    :returns: The string returned by *fn*, or a formatted error message.
    """
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        return f"Invalid project configuration for '{stack_path}': {e}"
    except SceptreException as e:
        return f"Sceptre error for '{stack_path}': {type(e).__name__}: {e}"
    except Exception as e:
        return f"Unexpected error for '{stack_path}': {type(e).__name__}: {e}"


def _execute_tool(
    sceptre_project_dir: str,
    stack_path: str,
    command: str,
    *args,
    ignore_dependencies: bool = False,
) -> str:
    """Execute a Sceptre command with standard error handling.

    Central helper that all tool functions delegate to. Runs the command,
    formats the response, and catches all expected exception types.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :param command: Name of the SceptrePlan method to invoke.
    :param args: Additional positional arguments forwarded to the plan command.
    :param ignore_dependencies: If True, skip dependency resolution.
    :returns: Formatted result string or error message.
    """

    def _run():
        result = _run_sceptre_command(
            sceptre_project_dir,
            stack_path,
            command,
            *args,
            ignore_dependencies=ignore_dependencies,
        )
        return _format_response(result, command)

    return _safe_execute(stack_path, _run)


@mcp.tool()
def create_stack(sceptre_project_dir: str, stack_path: str) -> str:
    """Create a CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack name and status.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "create")


@mcp.tool()
def update_stack(sceptre_project_dir: str, stack_path: str) -> str:
    """Update an existing CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack name and status.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "update")


@mcp.tool()
def delete_stack(sceptre_project_dir: str, stack_path: str) -> str:
    """Delete a CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack name and status.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "delete")


@mcp.tool()
def launch_stack(sceptre_project_dir: str, stack_path: str) -> str:
    """Launch a CloudFormation stack via Sceptre (create or update as needed).

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack name and status.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "launch")


@mcp.tool()
def get_stack_status(sceptre_project_dir: str, stack_path: str) -> str:
    """Get the current status of a CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack name and current CloudFormation status.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "get_status")


@mcp.tool()
def describe_stack(sceptre_project_dir: str, stack_path: str) -> str:
    """Describe a CloudFormation stack via Sceptre, returning full stack details.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack description details.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "describe")


@mcp.tool()
def describe_stack_outputs(sceptre_project_dir: str, stack_path: str) -> str:
    """Retrieve the outputs of a CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack output keys and values.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "describe_outputs")


@mcp.tool()
def describe_stack_resources(sceptre_project_dir: str, stack_path: str) -> str:
    """List the resources in a CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with resource identifiers, types, and statuses.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "describe_resources")


@mcp.tool()
def describe_stack_events(sceptre_project_dir: str, stack_path: str) -> str:
    """Retrieve the events for a CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result with stack event records.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "describe_events")


@mcp.tool()
def generate_template(sceptre_project_dir: str, stack_path: str) -> str:
    """Generate a CloudFormation template from a Sceptre stack configuration.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result containing the rendered CloudFormation template body.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "generate")


@mcp.tool()
def validate_template(sceptre_project_dir: str, stack_path: str) -> str:
    """Validate a CloudFormation template via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Validation result or error details.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "validate")


@mcp.tool()
def diff_stack(
    sceptre_project_dir: str,
    stack_path: str,
    diff_type: str = "deepdiff",
) -> str:
    """Diff a CloudFormation stack's local template against its deployed state via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :param diff_type: Type of differ to use: "deepdiff" (default) or "difflib".
    :returns: Formatted diff output or error message.
    """
    if diff_type not in ("deepdiff", "difflib"):
        return f"Invalid diff_type '{diff_type}'. Must be 'deepdiff' or 'difflib'."

    def _run():
        if diff_type == "difflib":
            stack_differ = DifflibStackDiffer()
            writer_class = DiffLibWriter
        else:
            stack_differ = DeepDiffStackDiffer()
            writer_class = DeepDiffWriter

        diffs = _run_sceptre_command(
            sceptre_project_dir, stack_path, "diff", stack_differ
        )

        output_buffer = io.StringIO()
        for stack_diff in diffs.values():
            writer = writer_class(stack_diff, output_buffer, "yaml")
            writer.write()

        return (
            output_buffer.getvalue().strip()
            or f"No differences found for '{stack_path}'."
        )

    return _safe_execute(stack_path, _run)


@mcp.tool()
def drift_detect(sceptre_project_dir: str, stack_path: str) -> str:
    """Detect configuration drift on a deployed CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Drift detection status or error message.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "drift_detect")


@mcp.tool()
def drift_show(
    sceptre_project_dir: str,
    stack_path: str,
    drifted_only: bool = False,
) -> str:
    """Show drift details for a deployed CloudFormation stack via Sceptre.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :param drifted_only: If True, only show resources that have drifted.
    :returns: Resource-level drift details or error message.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "drift_show", drifted_only)


@mcp.tool()
def list_stacks(sceptre_project_dir: str, stack_path: str = "") -> str:
    """List available stacks in a Sceptre project.

    Scans the project configuration and returns all stack names with their
    corresponding CloudFormation external names.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Optional relative path to scope listing to a stack group.
        Defaults to "" (all stacks).
    :returns: Formatted list of stacks with names and external names.
    """

    def _run():
        plan = _build_plan(sceptre_project_dir, stack_path)
        plan.resolve(command="list")

        stacks = {}
        for stack in plan.graph:
            stacks[stack.name] = stack.external_name

        if not stacks:
            return f"No stacks found for path '{stack_path or '(all)'}'."

        lines = [f"Stacks in '{stack_path or '(all)'}':"]
        for name, external_name in sorted(stacks.items()):
            lines.append(f"  {name} -> {external_name}")
        return "\n".join(lines)

    return _safe_execute(stack_path or "(all)", _run)


@mcp.tool()
def dump_config(sceptre_project_dir: str, stack_path: str) -> str:
    """Dump the resolved Sceptre configuration for a stack.

    :param sceptre_project_dir: Path to the Sceptre project directory.
    :param stack_path: Relative path to the stack config within the project.
    :returns: Formatted result containing the fully resolved stack configuration.
    """
    return _execute_tool(sceptre_project_dir, stack_path, "dump_config")


def main():
    """Entry point for the sceptre-mcp-server console script."""
    mcp.run()

"""Tests for sceptre_mcp_server.server."""

from datetime import datetime
from enum import Enum
from unittest.mock import MagicMock, patch

import pytest

from sceptre.exceptions import SceptreException

from sceptre_mcp_server.server import (
    _format_response,
    _make_serializable,
    _run_sceptre_command,
    _validate_project_dir,
    describe_stack,
    describe_stack_events,
    describe_stack_outputs,
    describe_stack_resources,
    get_stack_status,
    mcp,
)

# Unwrap FunctionTool objects to get the callable functions
_get_stack_status = get_stack_status.fn
_describe_stack = describe_stack.fn
_describe_stack_outputs = describe_stack_outputs.fn
_describe_stack_resources = describe_stack_resources.fn
_describe_stack_events = describe_stack_events.fn


def test_server_name():
    """Verify the FastMCP server is named correctly."""
    assert mcp.name == "sceptre-mcp-server"


# --- _validate_project_dir tests ---


class TestValidateProjectDir:
    def test_valid_project_dir(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        _validate_project_dir(str(tmp_path))

    def test_missing_directory(self):
        with pytest.raises(ValueError, match="does not exist"):
            _validate_project_dir("/nonexistent/path/to/project")

    def test_missing_config_subdirectory(self, tmp_path):
        with pytest.raises(ValueError, match="does not contain a config/ subdirectory"):
            _validate_project_dir(str(tmp_path))


# --- _make_serializable tests ---


class TestMakeSerializable:
    def test_enum_value(self):
        class Color(Enum):
            RED = "red"

        assert _make_serializable(Color.RED) == "red"

    def test_datetime_value(self):
        dt = datetime(2025, 1, 15, 10, 30, 0)
        assert _make_serializable(dt) == "2025-01-15T10:30:00"

    def test_nested_dict(self):
        class Status(Enum):
            OK = "ok"

        data = {"stack": {"status": Status.OK, "time": datetime(2025, 1, 1)}}
        result = _make_serializable(data)
        assert result == {"stack": {"status": "ok", "time": "2025-01-01T00:00:00"}}

    def test_list_with_mixed_types(self):
        class Status(Enum):
            DONE = "done"

        data = [Status.DONE, datetime(2025, 6, 1), "plain", 42]
        result = _make_serializable(data)
        assert result == ["done", "2025-06-01T00:00:00", "plain", 42]

    def test_tuple_converted(self):
        result = _make_serializable((1, "two", 3))
        assert result == [1, "two", 3]

    def test_plain_values_passthrough(self):
        assert _make_serializable("hello") == "hello"
        assert _make_serializable(42) == 42
        assert _make_serializable(None) is None


# --- _format_response tests ---


class TestFormatResponse:
    def test_string_response(self):
        result = {"my-project/dev/vpc": "CREATE_COMPLETE"}
        output = _format_response(result, "create")
        assert "Stack: my-project/dev/vpc" in output
        assert "Command: create" in output
        assert "Status: CREATE_COMPLETE" in output

    def test_dict_response_as_json(self):
        result = {"my-project/dev/vpc": {"StackId": "arn:aws:...", "Status": "ok"}}
        output = _format_response(result, "describe")
        assert "Stack: my-project/dev/vpc" in output
        assert "Command: describe" in output
        assert '"StackId": "arn:aws:..."' in output

    def test_enum_in_response(self):
        class StackStatus(Enum):
            COMPLETE = "complete"

        result = {"my-stack": StackStatus.COMPLETE}
        output = _format_response(result, "get_status")
        assert "Status: complete" in output

    def test_datetime_in_response(self):
        result = {"my-stack": {"CreationTime": datetime(2025, 3, 20, 12, 0, 0)}}
        output = _format_response(result, "describe")
        assert "2025-03-20T12:00:00" in output

    def test_multiple_stacks(self):
        result = {"stack-a": "CREATE_COMPLETE", "stack-b": "UPDATE_COMPLETE"}
        output = _format_response(result, "launch")
        assert "Stack: stack-a" in output
        assert "Stack: stack-b" in output
        assert "Status: CREATE_COMPLETE" in output
        assert "Status: UPDATE_COMPLETE" in output

    def test_empty_result(self):
        output = _format_response({}, "create")
        assert output == ""


# --- _run_sceptre_command tests ---


class TestRunSceptreCommand:
    def test_invalid_project_dir_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            _run_sceptre_command("/nonexistent", "dev/vpc.yaml", "create")

    def test_missing_config_raises(self, tmp_path):
        with pytest.raises(ValueError, match="does not contain a config/"):
            _run_sceptre_command(str(tmp_path), "dev/vpc.yaml", "create")

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_executes_command(self, mock_context_cls, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.create.return_value = {"my-stack": "CREATE_COMPLETE"}
        mock_plan_cls.return_value = mock_plan

        result = _run_sceptre_command(str(tmp_path), "dev/vpc.yaml", "create")

        mock_context_cls.assert_called_once_with(
            project_path=str(tmp_path),
            command_path="dev/vpc.yaml",
            ignore_dependencies=False,
        )
        mock_plan.create.assert_called_once()
        assert result == {"my-stack": "CREATE_COMPLETE"}

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_passes_extra_args(self, mock_context_cls, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.create_change_set.return_value = {"stack": "ok"}
        mock_plan_cls.return_value = mock_plan

        _run_sceptre_command(
            str(tmp_path), "dev/vpc.yaml", "create_change_set", "my-cs"
        )

        mock_plan.create_change_set.assert_called_once_with("my-cs")

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_ignore_dependencies(self, mock_context_cls, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.delete.return_value = {}
        mock_plan_cls.return_value = mock_plan

        _run_sceptre_command(
            str(tmp_path), "dev/vpc.yaml", "delete", ignore_dependencies=True
        )

        mock_context_cls.assert_called_once_with(
            project_path=str(tmp_path),
            command_path="dev/vpc.yaml",
            ignore_dependencies=True,
        )


# --- Query tool tests ---


class TestGetStackStatus:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.get_status.return_value = {"my-stack": "CREATE_COMPLETE"}
        mock_plan_cls.return_value = mock_plan

        result = _get_stack_status(str(tmp_path), "dev/vpc.yaml")

        mock_plan.get_status.assert_called_once()
        assert "Stack: my-stack" in result
        assert "Status: CREATE_COMPLETE" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.get_status.side_effect = SceptreException("Stack does not exist")
        mock_plan_cls.return_value = mock_plan

        result = _get_stack_status(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _get_stack_status("/nonexistent", "dev/vpc.yaml")
        assert "Unexpected error" in result
        assert "dev/vpc.yaml" in result


class TestDescribeStack:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe.return_value = {
            "my-stack": {
                "StackId": "arn:aws:stack/123",
                "StackStatus": "CREATE_COMPLETE",
            }
        }
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack(str(tmp_path), "dev/vpc.yaml")

        mock_plan.describe.assert_called_once()
        assert "Stack: my-stack" in result
        assert "arn:aws:stack/123" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe.side_effect = SceptreException("fail")
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result


class TestDescribeStackOutputs:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_outputs.return_value = {
            "my-stack": [{"OutputKey": "VpcId", "OutputValue": "vpc-123"}]
        }
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_outputs(str(tmp_path), "dev/vpc.yaml")

        mock_plan.describe_outputs.assert_called_once()
        assert "Stack: my-stack" in result
        assert "VpcId" in result
        assert "vpc-123" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_outputs.side_effect = SceptreException("no outputs")
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_outputs(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result


class TestDescribeStackResources:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_resources.return_value = {
            "my-stack": [
                {
                    "LogicalResourceId": "MyVpc",
                    "PhysicalResourceId": "vpc-abc",
                    "ResourceType": "AWS::EC2::VPC",
                    "ResourceStatus": "CREATE_COMPLETE",
                }
            ]
        }
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_resources(str(tmp_path), "dev/vpc.yaml")

        mock_plan.describe_resources.assert_called_once()
        assert "Stack: my-stack" in result
        assert "MyVpc" in result
        assert "AWS::EC2::VPC" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_resources.side_effect = SceptreException("fail")
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_resources(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result


class TestDescribeStackEvents:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_events.return_value = {
            "my-stack": [
                {
                    "EventId": "evt-1",
                    "ResourceStatus": "CREATE_COMPLETE",
                    "LogicalResourceId": "MyVpc",
                }
            ]
        }
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_events(str(tmp_path), "dev/vpc.yaml")

        mock_plan.describe_events.assert_called_once()
        assert "Stack: my-stack" in result
        assert "evt-1" in result
        assert "MyVpc" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_events.side_effect = SceptreException("fail")
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_events(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.describe_events.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _describe_stack_events(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result

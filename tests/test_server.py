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
    create_stack,
    delete_stack,
    describe_stack,
    describe_stack_events,
    describe_stack_outputs,
    describe_stack_resources,
    diff_stack,
    drift_detect,
    drift_show,
    dump_config,
    generate_template,
    get_stack_status,
    launch_stack,
    list_stacks,
    mcp,
    update_stack,
    validate_template,
)

# Unwrap FunctionTool objects to get the callable functions
_create_stack = create_stack.fn
_update_stack = update_stack.fn
_delete_stack = delete_stack.fn
_launch_stack = launch_stack.fn
_get_stack_status = get_stack_status.fn
_describe_stack = describe_stack.fn
_describe_stack_outputs = describe_stack_outputs.fn
_describe_stack_resources = describe_stack_resources.fn
_describe_stack_events = describe_stack_events.fn
_generate_template = generate_template.fn
_validate_template = validate_template.fn
_diff_stack = diff_stack.fn
_drift_detect = drift_detect.fn
_drift_show = drift_show.fn
_list_stacks = list_stacks.fn
_dump_config = dump_config.fn


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


# --- Lifecycle tool tests ---


class TestCreateStack:
    def test_invalid_project_dir(self):
        result = _create_stack("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


class TestUpdateStack:
    def test_invalid_project_dir(self):
        result = _update_stack("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


class TestDeleteStack:
    def test_invalid_project_dir(self):
        result = _delete_stack("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


class TestLaunchStack:
    def test_invalid_project_dir(self):
        result = _launch_stack("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


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
        assert "Invalid project configuration" in result
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

    def test_invalid_project_dir(self):
        result = _describe_stack("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


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

    def test_invalid_project_dir(self):
        result = _describe_stack_outputs("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


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

    def test_invalid_project_dir(self):
        result = _describe_stack_resources("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result


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

    def test_invalid_project_dir(self):
        result = _describe_stack_events("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

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


# --- Template tool tests ---


class TestGenerateTemplate:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.generate.return_value = {
            "my-stack": {"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}
        }
        mock_plan_cls.return_value = mock_plan

        result = _generate_template(str(tmp_path), "dev/vpc.yaml")

        mock_plan.generate.assert_called_once()
        assert "Stack: my-stack" in result
        assert "AWSTemplateFormatVersion" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.generate.side_effect = SceptreException("template not found")
        mock_plan_cls.return_value = mock_plan

        result = _generate_template(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _generate_template("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.generate.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _generate_template(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result


class TestValidateTemplate:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.validate.return_value = {
            "my-stack": {
                "ResponseMetadata": {"RequestId": "abc-123"},
                "Parameters": [],
            }
        }
        mock_plan_cls.return_value = mock_plan

        result = _validate_template(str(tmp_path), "dev/vpc.yaml")

        mock_plan.validate.assert_called_once()
        assert "Stack: my-stack" in result
        assert "abc-123" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.validate.side_effect = SceptreException("validation failed")
        mock_plan_cls.return_value = mock_plan

        result = _validate_template(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _validate_template("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.validate.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _validate_template(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result


# --- Diff and Drift tool tests ---


class TestDiffStack:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    @patch("sceptre_mcp_server.server.DeepDiffWriter")
    @patch("sceptre_mcp_server.server.DeepDiffStackDiffer")
    def test_success_deepdiff(
        self, mock_differ_cls, mock_writer_cls, mock_ctx, mock_plan_cls, tmp_path
    ):
        (tmp_path / "config").mkdir()
        mock_differ = MagicMock()
        mock_differ_cls.return_value = mock_differ

        mock_stack_diff = MagicMock()
        mock_plan = MagicMock()
        mock_plan.diff.return_value = {"my-stack": mock_stack_diff}
        mock_plan_cls.return_value = mock_plan

        mock_writer = MagicMock()

        def write_side_effect():
            # Simulate writer writing to the buffer
            args = mock_writer_cls.call_args
            output_stream = args[0][1]
            output_stream.write("Difference detected for stack my-stack\n")

        mock_writer.write.side_effect = write_side_effect
        mock_writer_cls.return_value = mock_writer

        result = _diff_stack(str(tmp_path), "dev/vpc.yaml")

        mock_differ_cls.assert_called_once()
        mock_plan.diff.assert_called_once_with(mock_differ)
        mock_writer_cls.assert_called_once()
        assert "Difference detected" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    @patch("sceptre_mcp_server.server.DiffLibWriter")
    @patch("sceptre_mcp_server.server.DifflibStackDiffer")
    def test_success_difflib(
        self, mock_differ_cls, mock_writer_cls, mock_ctx, mock_plan_cls, tmp_path
    ):
        (tmp_path / "config").mkdir()
        mock_differ = MagicMock()
        mock_differ_cls.return_value = mock_differ

        mock_stack_diff = MagicMock()
        mock_plan = MagicMock()
        mock_plan.diff.return_value = {"my-stack": mock_stack_diff}
        mock_plan_cls.return_value = mock_plan

        mock_writer = MagicMock()

        def write_side_effect():
            args = mock_writer_cls.call_args
            output_stream = args[0][1]
            output_stream.write("Difflib difference for stack my-stack\n")

        mock_writer.write.side_effect = write_side_effect
        mock_writer_cls.return_value = mock_writer

        result = _diff_stack(str(tmp_path), "dev/vpc.yaml", diff_type="difflib")

        mock_differ_cls.assert_called_once()
        mock_plan.diff.assert_called_once_with(mock_differ)
        mock_writer_cls.assert_called_once()
        mock_writer.write.assert_called_once()
        assert "Difflib difference" in result

    def test_invalid_diff_type(self, tmp_path):
        (tmp_path / "config").mkdir()
        result = _diff_stack(str(tmp_path), "dev/vpc.yaml", diff_type="invalid")
        assert "Invalid diff_type" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    @patch("sceptre_mcp_server.server.DeepDiffStackDiffer")
    def test_sceptre_error(self, mock_differ_cls, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.diff.side_effect = SceptreException("diff failed")
        mock_plan_cls.return_value = mock_plan

        result = _diff_stack(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _diff_stack("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    @patch("sceptre_mcp_server.server.DeepDiffStackDiffer")
    def test_unexpected_error(self, mock_differ_cls, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.diff.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _diff_stack(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result


class TestDriftDetect:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_detect.return_value = {"my-stack": "DETECTION_COMPLETE"}
        mock_plan_cls.return_value = mock_plan

        result = _drift_detect(str(tmp_path), "dev/vpc.yaml")

        mock_plan.drift_detect.assert_called_once()
        assert "Stack: my-stack" in result
        assert "DETECTION_COMPLETE" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_detect.side_effect = SceptreException("drift failed")
        mock_plan_cls.return_value = mock_plan

        result = _drift_detect(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _drift_detect("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_detect.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _drift_detect(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result


class TestDriftShow:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_show.return_value = {
            "my-stack": {
                "StackResourceDriftStatus": "MODIFIED",
                "LogicalResourceId": "MyVpc",
            }
        }
        mock_plan_cls.return_value = mock_plan

        result = _drift_show(str(tmp_path), "dev/vpc.yaml")

        mock_plan.drift_show.assert_called_once_with(False)
        assert "Stack: my-stack" in result
        assert "MyVpc" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_drifted_only(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_show.return_value = {"my-stack": {"Status": "DRIFTED"}}
        mock_plan_cls.return_value = mock_plan

        result = _drift_show(str(tmp_path), "dev/vpc.yaml", drifted_only=True)

        mock_plan.drift_show.assert_called_once_with(True)
        assert "Stack: my-stack" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_show.side_effect = SceptreException("drift show failed")
        mock_plan_cls.return_value = mock_plan

        result = _drift_show(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _drift_show("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.drift_show.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _drift_show(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result


# --- Discovery and Configuration tool tests ---


class TestListStacks:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()

        stack_a = MagicMock()
        stack_a.name = "dev/vpc"
        stack_a.external_name = "my-project-dev-vpc"
        stack_b = MagicMock()
        stack_b.name = "dev/app"
        stack_b.external_name = "my-project-dev-app"

        mock_plan = MagicMock()
        mock_plan.graph.__iter__ = MagicMock(return_value=iter([stack_a, stack_b]))
        mock_plan_cls.return_value = mock_plan

        result = _list_stacks(str(tmp_path))

        mock_plan.resolve.assert_called_once_with(command="list")
        assert "dev/vpc" in result
        assert "my-project-dev-vpc" in result
        assert "dev/app" in result
        assert "my-project-dev-app" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success_with_stack_path(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()

        stack = MagicMock()
        stack.name = "dev/vpc"
        stack.external_name = "my-project-dev-vpc"

        mock_plan = MagicMock()
        mock_plan.graph.__iter__ = MagicMock(return_value=iter([stack]))
        mock_plan_cls.return_value = mock_plan

        result = _list_stacks(str(tmp_path), stack_path="dev")

        mock_ctx.assert_called_once_with(
            project_path=str(tmp_path),
            command_path="dev",
            ignore_dependencies=False,
        )
        assert "dev/vpc" in result
        assert "my-project-dev-vpc" in result
        assert "'dev'" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_empty_graph(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.graph.__iter__ = MagicMock(return_value=iter([]))
        mock_plan_cls.return_value = mock_plan

        result = _list_stacks(str(tmp_path))

        assert "No stacks found" in result
        assert "(all)" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_empty_graph_with_stack_path(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.graph.__iter__ = MagicMock(return_value=iter([]))
        mock_plan_cls.return_value = mock_plan

        result = _list_stacks(str(tmp_path), stack_path="prod")

        assert "No stacks found" in result
        assert "'prod'" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.resolve.side_effect = SceptreException("graph error")
        mock_plan_cls.return_value = mock_plan

        result = _list_stacks(str(tmp_path))

        assert "Sceptre error" in result

    def test_invalid_project_dir(self):
        result = _list_stacks("/nonexistent")
        assert "Invalid project configuration" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.resolve.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _list_stacks(str(tmp_path))

        assert "Unexpected error" in result
        assert "RuntimeError" in result


class TestDumpConfig:
    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_success(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.dump_config.return_value = {
            "my-stack": {
                "template_path": "templates/vpc.yaml",
                "parameters": {"CidrBlock": "10.0.0.0/16"},
            }
        }
        mock_plan_cls.return_value = mock_plan

        result = _dump_config(str(tmp_path), "dev/vpc.yaml")

        mock_plan.dump_config.assert_called_once()
        assert "Stack: my-stack" in result
        assert "template_path" in result
        assert "10.0.0.0/16" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_sceptre_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.dump_config.side_effect = SceptreException("config error")
        mock_plan_cls.return_value = mock_plan

        result = _dump_config(str(tmp_path), "dev/vpc.yaml")

        assert "Sceptre error" in result
        assert "dev/vpc.yaml" in result

    def test_invalid_project_dir(self):
        result = _dump_config("/nonexistent", "dev/vpc.yaml")
        assert "Invalid project configuration" in result
        assert "dev/vpc.yaml" in result

    @patch("sceptre_mcp_server.server.SceptrePlan")
    @patch("sceptre_mcp_server.server.SceptreContext")
    def test_unexpected_error(self, mock_ctx, mock_plan_cls, tmp_path):
        (tmp_path / "config").mkdir()
        mock_plan = MagicMock()
        mock_plan.dump_config.side_effect = RuntimeError("boom")
        mock_plan_cls.return_value = mock_plan

        result = _dump_config(str(tmp_path), "dev/vpc.yaml")

        assert "Unexpected error" in result
        assert "RuntimeError" in result

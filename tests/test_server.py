"""Tests for sceptre_mcp_server.server."""

from sceptre_mcp_server.server import mcp


def test_server_name():
    """Verify the FastMCP server is named correctly."""
    assert mcp.name == "sceptre-mcp-server"

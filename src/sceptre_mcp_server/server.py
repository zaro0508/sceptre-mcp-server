"""sceptre-mcp-server: MCP server exposing Sceptre CloudFormation operations as tools."""

from fastmcp import FastMCP

mcp = FastMCP("sceptre-mcp-server")


def main():
    """Entry point for the sceptre-mcp-server console script."""
    mcp.run()

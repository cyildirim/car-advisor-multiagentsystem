#!/usr/bin/env python3
"""
Run the MCP server locally in HTTP mode for development.
Use this when you want to test the agent integration locally.
"""
import os
os.environ["PORT"] = "8080"  # Force HTTP mode

# Now import and run the server
from server import mcp

if __name__ == "__main__":
    print("Starting MCP server in HTTP mode on http://127.0.0.1:8080")
    mcp.run(transport="streamable-http")

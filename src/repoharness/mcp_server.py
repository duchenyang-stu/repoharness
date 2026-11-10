"""Minimal MCP 2024-11-05 stdio server for RepoHarness tools."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .tools import ToolRegistry, build_repository_tools


class MCPServer:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        if request_id is None:
            return None
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "repoharness", "version": "0.2.0"},
                }
            elif method == "tools/list":
                result = {"tools": self.tools.mcp_tools()}
            elif method == "tools/call":
                params = request.get("params", {})
                output = self.tools.get(params["name"]).invoke(params.get("arguments", {}))
                result = {
                    "content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}],
                    "isError": not output["ok"],
                }
            elif method == "ping":
                result = {}
            else:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32602, "message": f"{type(exc).__name__}: {exc}"},
            }


def serve_stdio(server: MCPServer) -> None:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle(request)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RepoHarness tools over MCP stdio")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    serve_stdio(MCPServer(build_repository_tools(args.workspace)))


if __name__ == "__main__":
    main()


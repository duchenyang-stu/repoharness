from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repoharness.mcp_server import MCPServer
from repoharness.tools import build_repository_tools


class MCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "sample.py").write_text("answer = 42\n", encoding="utf-8")
        self.server = MCPServer(build_repository_tools(self.root))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_initialize_declares_protocol_and_tools(self):
        result = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(result["result"]["protocolVersion"], "2024-11-05")
        listed = self.server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(listed["result"]["tools"]), 5)

    def test_tool_call_returns_mcp_content(self):
        response = self.server.handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "search_repo", "arguments": {"query": "42"}},
        })
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(response["result"]["content"][0]["type"], "text")

    def test_unknown_method_is_json_rpc_error(self):
        response = self.server.handle({"jsonrpc": "2.0", "id": 4, "method": "missing"})
        self.assertEqual(response["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()


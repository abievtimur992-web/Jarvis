"""
test_mcp_client.py — mcp_client.py ushın stdlib unittest testleri.

Haqıyqıy tarmaq shaqırıwı islenbeydi — urllib.request.urlopen mock
etiledi (unittest.mock), MCP_SERVER_URL/MCP_API_KEY sazlanbaǵanda
dawam etiwdi tekseredi.
"""

import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch

import mcp_client


class ParseResponseBodyTestCase(unittest.TestCase):
    def test_plain_json(self):
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})
        message = mcp_client.parse_response_body("application/json", raw)
        self.assertEqual(message["result"], {"ok": True})

    def test_sse_single_event(self):
        raw = 'data: {"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}\n\n'
        message = mcp_client.parse_response_body("text/event-stream", raw)
        self.assertEqual(message["result"], {"ok": True})

    def test_sse_multiple_events_returns_last(self):
        raw = (
            'data: {"jsonrpc": "2.0", "method": "notifications/x"}\n\n'
            'data: {"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}\n\n'
        )
        message = mcp_client.parse_response_body("text/event-stream", raw)
        self.assertEqual(message["result"], {"ok": True})

    def test_sse_no_data_lines_raises(self):
        with self.assertRaises(mcp_client.MCPError):
            mcp_client.parse_response_body("text/event-stream", "\n\n")

    def test_invalid_json_raises(self):
        with self.assertRaises(mcp_client.MCPError):
            mcp_client.parse_response_body("application/json", "bul JSON emes")


class IsConfiguredTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in ("MCP_SERVER_URL", "MCP_API_KEY")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_not_configured_by_default(self):
        self.assertFalse(mcp_client.is_configured())

    def test_configured_when_both_present(self):
        os.environ["MCP_SERVER_URL"] = "https://connect.composio.dev/mcp"
        os.environ["MCP_API_KEY"] = "sınaw-kilit"
        self.assertTrue(mcp_client.is_configured())

    def test_not_configured_with_only_one(self):
        os.environ["MCP_SERVER_URL"] = "https://connect.composio.dev/mcp"
        self.assertFalse(mcp_client.is_configured())


class CallToolTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in ("MCP_SERVER_URL", "MCP_API_KEY")}
        mcp_client._initialized = False
        mcp_client._session_id = None
        mcp_client._TOOLS_CACHE = None

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        mcp_client._initialized = False
        mcp_client._session_id = None
        mcp_client._TOOLS_CACHE = None

    def test_not_configured_reports_clearly_no_crash(self):
        result = mcp_client.call_tool("gmail_send", {"to": "x@x.com"})
        self.assertIn("gmail_send", result["card"]["tool"])
        self.assertTrue(result["card"]["error"])
        self.assertIn("qátelik", result["spoken"])

    def _fake_response(self, body: dict, content_type: str = "application/json", session_id=None):
        class _FakeResp(BytesIO):
            def __init__(self, data, headers):
                super().__init__(data)
                self.headers = headers

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        headers = {"Content-Type": content_type}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return _FakeResp(json.dumps(body).encode("utf-8"), headers)

    def test_successful_call_with_mocked_transport(self):
        os.environ["MCP_SERVER_URL"] = "https://connect.composio.dev/mcp"
        os.environ["MCP_API_KEY"] = "sınaw-kilit"

        responses = [
            self._fake_response(
                {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}},
                session_id="sess-1",
            ),
            self._fake_response({}),  # notifications/initialized — expect_response=False, oqılmaydı
            self._fake_response(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {"content": [{"type": "text", "text": "Jiberildi."}], "isError": False},
                }
            ),
        ]

        with patch("mcp_client._urlopen_retrying", side_effect=responses):
            result = mcp_client.call_tool("gmail_send", {"to": "x@x.com"})

        self.assertEqual(result["card"]["tool"], "gmail_send")
        self.assertEqual(result["card"]["source"], "mcp")
        self.assertFalse(result["card"]["is_error"])
        self.assertIn("Jiberildi", result["card"]["result"])


if __name__ == "__main__":
    unittest.main()

"""
test_main.py — main.py-dagı sáwbet tarıyxı funktsiyaları ushın testler.

OpenAI API-ge haqıyqıy tarmaq shaqırıwı islenbeydi (OPENAI_API_KEY joq
bolsa da, main import etiledi — bul jerdegi testler tek _CONVERSATION penen
islesetuǵın taza funktsiyalardı tekseredi).
"""

import unittest

import main


class IsTurnStartTestCase(unittest.TestCase):
    def test_user_message_is_turn_start(self):
        self.assertTrue(main._is_turn_start({"role": "user", "content": "soraw"}))

    def test_assistant_message_is_not_turn_start(self):
        self.assertFalse(
            main._is_turn_start({"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]})
        )

    def test_tool_result_message_is_not_turn_start(self):
        self.assertFalse(main._is_turn_start({"role": "tool", "tool_call_id": "t1", "content": "nátiyje"}))


class TrimHistoryTestCase(unittest.TestCase):
    def setUp(self):
        main._CONVERSATION.clear()

    def tearDown(self):
        main._CONVERSATION.clear()

    def test_cut_point_always_lands_on_a_user_turn_start(self):
        # Eki gezek: biri tool-shaqırıw/tool-nátiyje jubı menen, biri ápiwayı.
        main._CONVERSATION.extend(
            [
                {"role": "user", "content": "1-soraw"},
                {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]},
                {"role": "tool", "tool_call_id": "t1", "content": "nátiyje"},
                {"role": "assistant", "content": "juwap1"},
                {"role": "user", "content": "2-soraw"},
                {"role": "assistant", "content": "juwap2"},
            ]
        )
        # MAX_HISTORY_TURNS * 2 -den úlken qılıw ushın ulıwma shekti waqıtsha kishireytemiz
        old_limit = main.MAX_HISTORY_TURNS
        main.MAX_HISTORY_TURNS = 1
        try:
            main._trim_history()
        finally:
            main.MAX_HISTORY_TURNS = old_limit

        self.assertTrue(main._is_turn_start(main._CONVERSATION[0]))
        # Tool-nátiyje jubı bólinbegen — "tool" xabarı "assistant"-sız qalmaǵan
        roles = [m["role"] for m in main._CONVERSATION]
        if "tool" in roles:
            tool_idx = roles.index("tool")
            self.assertEqual(roles[tool_idx - 1], "assistant")

    def test_short_history_is_not_trimmed(self):
        main._CONVERSATION.extend(
            [
                {"role": "user", "content": "soraw"},
                {"role": "assistant", "content": "juwap"},
            ]
        )
        main._trim_history()
        self.assertEqual(len(main._CONVERSATION), 2)


class ToolsForApiTestCase(unittest.TestCase):
    def test_converts_to_openai_function_calling_shape(self):
        main._TOOLS_FOR_API = None  # keshti tazalap, qaytadan qurıwǵa májbúrlew
        tools = main._tools_for_api()
        self.assertTrue(tools)
        for t in tools:
            self.assertEqual(t["type"], "function")
            self.assertIn("name", t["function"])
            self.assertIn("description", t["function"])
            self.assertIn("parameters", t["function"])

    def test_includes_search_brain(self):
        main._TOOLS_FOR_API = None
        tools = main._tools_for_api()
        names = {t["function"]["name"] for t in tools}
        self.assertIn("search_brain", names)


class IsOpenAICompatibleSchemaTestCase(unittest.TestCase):
    def test_plain_object_schema_is_compatible(self):
        self.assertTrue(
            main._is_openai_compatible_schema({"type": "object", "properties": {"q": {"type": "string"}}})
        )

    def test_top_level_oneof_is_not_compatible(self):
        self.assertFalse(main._is_openai_compatible_schema({"oneOf": [{"type": "object"}]}))

    def test_top_level_anyof_is_not_compatible(self):
        self.assertFalse(main._is_openai_compatible_schema({"anyOf": [{"type": "string"}]}))

    def test_non_object_type_is_not_compatible(self):
        self.assertFalse(main._is_openai_compatible_schema({"type": "string"}))

    def test_non_dict_is_not_compatible(self):
        self.assertFalse(main._is_openai_compatible_schema(None))
        self.assertFalse(main._is_openai_compatible_schema("bul schema emes"))

    def test_mcp_tool_with_broken_schema_is_skipped_others_kept(self):
        main._TOOLS_FOR_API = None

        class _FakeMCP:
            @staticmethod
            def is_configured():
                return True

            @staticmethod
            def list_tools():
                return [
                    {"name": "COMPOSIO_MANAGE_SKILL", "description": "qáte", "inputSchema": {"oneOf": []}},
                    {
                        "name": "gmail_send",
                        "description": "jaqsı",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]

        original_mcp = main.mcp_mod
        main.mcp_mod = _FakeMCP
        try:
            tools = main._tools_for_api()
        finally:
            main.mcp_mod = original_mcp
            main._TOOLS_FOR_API = None

        names = {t["function"]["name"] for t in tools}
        self.assertNotIn("COMPOSIO_MANAGE_SKILL", names)
        self.assertIn("gmail_send", names)


if __name__ == "__main__":
    unittest.main()

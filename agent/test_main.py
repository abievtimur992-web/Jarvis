"""
test_main.py — main.py-dagı sáwbet tarıyxı funktsiyaları ushın testler.

Anthropic API-ge haqıyqıy tarmaq shaqırıwı islenbeydi (ANTHROPIC_API_KEY joq
bolsa da, main import etiledi — bul jerdegi testler tek _CONVERSATION penen
islesetuǵın taza funktsiyalardı tekseredi).
"""

import unittest

import main


class StripThinkingBlocksTestCase(unittest.TestCase):
    def setUp(self):
        main._CONVERSATION.clear()

    def tearDown(self):
        main._CONVERSATION.clear()

    def test_removes_thinking_and_redacted_thinking_keeps_others(self):
        main._CONVERSATION.append({"role": "user", "content": "soraw"})
        main._CONVERSATION.append(
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "...", "signature": "sig"},
                    {"type": "tool_use", "id": "t1", "name": "search_brain", "input": {}},
                ],
            }
        )
        main._CONVERSATION.append(
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "nátiyje"}]}
        )
        main._CONVERSATION.append(
            {
                "role": "assistant",
                "content": [
                    {"type": "redacted_thinking", "data": "..."},
                    {"type": "text", "text": "juwap"},
                ],
            }
        )

        main._strip_thinking_blocks(0)

        assistant_messages = [m for m in main._CONVERSATION if m["role"] == "assistant"]
        for message in assistant_messages:
            block_types = {b["type"] for b in message["content"]}
            self.assertNotIn("thinking", block_types)
            self.assertNotIn("redacted_thinking", block_types)
        self.assertEqual(assistant_messages[0]["content"][0]["type"], "tool_use")
        self.assertEqual(assistant_messages[1]["content"][0]["type"], "text")

    def test_does_not_touch_messages_before_start_index(self):
        main._CONVERSATION.append(
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "eski", "signature": "sig"}]}
        )
        main._CONVERSATION.append({"role": "user", "content": "jańa gezek"})
        main._CONVERSATION.append(
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "jańa", "signature": "sig2"}, {"type": "text", "text": "juwap"}]}
        )

        main._strip_thinking_blocks(1)

        self.assertEqual(main._CONVERSATION[0]["content"][0]["type"], "thinking")
        block_types = {b["type"] for b in main._CONVERSATION[2]["content"]}
        self.assertNotIn("thinking", block_types)

    def test_ignores_string_content_and_non_assistant_messages(self):
        main._CONVERSATION.append({"role": "user", "content": "tekst"})
        main._CONVERSATION.append({"role": "assistant", "content": "tekst juwap"})

        main._strip_thinking_blocks(0)  # qátelik shıǵarmaydı

        self.assertEqual(main._CONVERSATION[0]["content"], "tekst")
        self.assertEqual(main._CONVERSATION[1]["content"], "tekst juwap")


if __name__ == "__main__":
    unittest.main()

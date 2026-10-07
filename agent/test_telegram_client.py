"""
test_telegram_client.py — telegram_client.py ushın stdlib unittest
testleri. telethon bul sandboxta ornatılmaǵan — testler sonı durıs
jetkiziwdi (ImportError -> TelegramError) hám sazlaw tekseriwin
tekseredi, haqıyqıy MTProto baylanısın SINAMAYDI.
"""

import os
import unittest
from pathlib import Path

import telegram_client


class IsConfiguredTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_not_configured_without_env(self):
        self.assertFalse(telegram_client.is_configured())

    def test_not_configured_without_session_even_with_env(self):
        os.environ["TELEGRAM_API_ID"] = "12345"
        os.environ["TELEGRAM_API_HASH"] = "sınaw-hash"
        # telethon bul sandboxta joq hám/yamasa sessiya fayli joq —
        # eki jaǵdayda da False bolıwı kerek.
        self.assertFalse(telegram_client.is_configured())


class ClientErrorsTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_missing_env_raises_telegram_error(self):
        with self.assertRaises(telegram_client.TelegramError):
            telegram_client._client()

    def test_non_numeric_api_id_raises_telegram_error(self):
        os.environ["TELEGRAM_API_ID"] = "bul-san-emes"
        os.environ["TELEGRAM_API_HASH"] = "sınaw-hash"
        with self.assertRaises(telegram_client.TelegramError):
            telegram_client._client()

    def test_missing_telethon_raises_telegram_error_with_install_hint(self):
        # Bul sandboxta telethon ornatılmaǵan, sonıń ushın _telethon_client_class()
        # hámishe usı jolǵa túsedi — pip install usınısın tekseremiz.
        with self.assertRaises(telegram_client.TelegramError) as cm:
            telegram_client._telethon_client_class()
        self.assertIn("pip install telethon", str(cm.exception))

    def test_recent_messages_without_config_raises_telegram_error(self):
        with self.assertRaises(telegram_client.TelegramError):
            telegram_client.recent_messages("@x")

    def test_send_message_without_config_raises_telegram_error(self):
        with self.assertRaises(telegram_client.TelegramError):
            telegram_client.send_message("@x", "sálem")


class SessionPathTestCase(unittest.TestCase):
    def test_session_path_lives_under_memory_dir(self):
        self.assertEqual(telegram_client.SESSION_PATH.name, "telegram.session")
        self.assertEqual(telegram_client.SESSION_PATH.parent.name, "memory")


if __name__ == "__main__":
    unittest.main()

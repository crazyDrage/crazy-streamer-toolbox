import tempfile
import tomllib
import unittest
from pathlib import Path

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.security.remote_access import RemoteAccess


class TestRemoteAccess(unittest.TestCase):
    def test_password_first_then_open_saved_for_the_next_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toolbox.toml"
            access = RemoteAccess({"host": "127.0.0.1"}, {}, ConfigTableWriter(path))
            with self.assertRaisesRegex(ValueError, "password"):
                access.set_open(True)
            access.set_password("long enough")
            key = access.session_key()
            access.set_open(True)
            self.assertTrue(access.check("long enough"))
            self.assertFalse(access.check("wrong"))
            self.assertTrue(access.restart_needed)
            saved = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["api"]["host"], "0.0.0.0")
            self.assertNotIn("long enough", path.read_text(encoding="utf-8"))
            again = RemoteAccess(saved["api"], saved["access"], ConfigTableWriter(path))
            self.assertEqual((again.open, again.restart_needed, again.session_key()), (True, False, key))
            again.set_password("another one")
            self.assertNotEqual(again.session_key(), key)  # every device signs in again

    def test_this_pc(self) -> None:
        self.assertTrue(RemoteAccess.is_this_pc("127.0.0.1"))
        self.assertTrue(RemoteAccess.is_this_pc("::1"))
        self.assertFalse(RemoteAccess.is_this_pc("192.168.1.20"))
        self.assertFalse(RemoteAccess.is_this_pc(None))

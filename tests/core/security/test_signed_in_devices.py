import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.security.signed_in_devices import SignedInDevices


class TestSignedInDevices(unittest.TestCase):
    def test_kept_over_a_restart_old_passwords_dropped_sign_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "devices.json"
            devices = SignedInDevices(path)
            devices.add("phone", "key1")
            self.assertTrue(SignedInDevices(path).signed_in("phone", "key1"))
            self.assertFalse(devices.signed_in("phone", "key2"))
            self.assertFalse(devices.signed_in(None, "key1"))
            self.assertFalse(devices.signed_in("phone", ""))
            devices.add("laptop", "key2")  # a new password: the phone's old entry goes
            self.assertEqual(path.read_text(encoding="utf-8").count("key1"), 0)
            devices.remove("laptop")
            self.assertFalse(SignedInDevices(path).signed_in("laptop", "key2"))

    def test_a_broken_file_signs_everyone_out_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "devices.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertLogs(level="ERROR"):
                self.assertFalse(SignedInDevices(path).signed_in("phone", "key1"))

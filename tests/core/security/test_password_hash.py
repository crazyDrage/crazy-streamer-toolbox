import unittest

from streamer_toolbox.core.security.password_hash import PasswordHash


class TestPasswordHash(unittest.TestCase):
    def test_right_password_passes_wrong_and_broken_ones_fail(self) -> None:
        stored = PasswordHash.make("dragon-tail")
        self.assertNotIn("dragon-tail", stored)
        self.assertTrue(PasswordHash.verify(stored, "dragon-tail"))
        self.assertFalse(PasswordHash.verify(stored, "Dragon-tail"))
        self.assertFalse(PasswordHash.verify(stored, ""))
        self.assertFalse(PasswordHash.verify("", "dragon-tail"))
        self.assertFalse(PasswordHash.verify("nonsense", "dragon-tail"))
        self.assertNotEqual(PasswordHash.make("dragon-tail"), stored)  # a new salt each time
        with self.assertRaises(ValueError):
            PasswordHash.make("")

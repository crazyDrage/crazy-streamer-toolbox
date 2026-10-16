import unittest
from types import SimpleNamespace as Key

from streamer_toolbox.connections.keyboard.key_name import KeyName


class TestKeyName(unittest.TestCase):
    """Names like a flow trigger writes them, from pynput-like key objects (Key: .name, KeyCode: .char / .vk)."""

    def test_special_keys_letters_and_modifiers(self) -> None:
        self.assertEqual(KeyName.of(Key(name="f23"), set()), "f23")
        self.assertEqual(KeyName.of(Key(name=None, char="K", vk=0x4B), set()), "k")
        self.assertEqual(KeyName.of(Key(name=None, char="\x0b", vk=0x4B), {"shift", "ctrl"}), "ctrl+shift+k")
        self.assertEqual(KeyName.of(Key(name=None, char=None, vk=173), {"win"}), "win+vk173")
        self.assertEqual(KeyName.of(Key(name=None, char="#", vk=None), set()), "#")

    def test_a_name_is_taken_apart_and_put_together(self) -> None:
        self.assertEqual(KeyName.parts("Ctrl+Shift+K "), (["ctrl", "shift"], "k"))
        self.assertEqual(KeyName.parts("shift+ctrl+f23"), (["ctrl", "shift"], "f23"))
        self.assertEqual(KeyName.parts("f23"), ([], "f23"))
        self.assertEqual(KeyName.parts("ctrl++"), (["ctrl"], "+"))
        self.assertEqual(KeyName.parts(""), ([], ""))
        self.assertEqual(KeyName.join({"shift", "ctrl"}, "k"), "ctrl+shift+k")
        self.assertEqual(KeyName.join([], "f23"), "f23")

    def test_modifiers_and_text(self) -> None:
        self.assertEqual([KeyName.modifier(Key(name=n)) for n in ("ctrl_r", "alt_gr", "shift", "cmd", "f1")],
                         ["ctrl", "alt", "shift", "win", ""])
        self.assertTrue(KeyName.is_text("a"))
        self.assertFalse(KeyName.is_text("f23"))
        self.assertFalse(KeyName.is_text("ctrl+a"))

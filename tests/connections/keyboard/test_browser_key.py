import unittest

from streamer_toolbox.connections.keyboard.browser_key import BrowserKey


class TestBrowserKey(unittest.TestCase):
    def test_a_browser_key_gets_the_name_a_trigger_writes(self) -> None:
        self.assertEqual([BrowserKey.base(code, key) for code, key in (
            ("KeyK", "K"), ("KeyK", "\x0b"), ("Digit5", "%"), ("F23", "F23"), ("F5", "F5"), ("Space", " "),
            ("ArrowUp", "ArrowUp"), ("Escape", "Escape"), ("PageDown", "PageDown"),
            ("MediaPlayPause", "MediaPlayPause"), ("VolumeUp", "AudioVolumeUp"), ("Backslash", "#"),
            ("Minus", "-"))],
            ["k", "k", "5", "f23", "f5", "space", "up", "esc", "page_down", "media_play_pause",
             "media_volume_up", "#", "-"])

    def test_a_key_it_does_not_know_has_no_name(self) -> None:
        self.assertEqual([BrowserKey.base(code, key) for code, key in (
            ("Numpad1", "1"), ("NumpadAdd", "+"), ("BrowserBack", "BrowserBack"), ("", "Unidentified"))],
            ["", "", "", ""])


if __name__ == "__main__":
    unittest.main()

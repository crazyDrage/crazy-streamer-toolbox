import unittest

from streamer_toolbox.connections.vnyan.vnyan_copy_texts import PREFIX, VNyanCopyTexts, decode

# his exports (11-22, temp/feedback/vnyan/nyan_block.md)
HIS_DATA = ("VNYANGRAPH:VEIeZGF0YSBibG9jayAtIGNvbW1hbmQgVGV4dCBuZWVkcyB0byBzdGF5IGVtdHB5HjAeMB4tNDA5HzE5HjUyOR80MTccTWgeV2"
            "Vic29ja2V0HlRCHjAeLTI3OR8tMTIxHmNvbW1hbmQfHVFLHkRpY3Rpb25hcnlHZXRGbGV4HlRCHjAeLTEyMh8tMTU1Hm9wdHMfMR9uYW1l"
            "Hx9rMB9rZXkcHVFLMB9NaDI")
HIS_TEXT = ("VNYANGRAPH:bEoedGV4dCBibG9jayAtIGl0IHdpbGwgdHJpZ2dlciBpZiB0aGUgdGV4dCBzdGFydHMgd2l0aCB0aGUgY29tbWFuZCB0ZXh0Hj"
            "AeMB4tMTczHzE0HjQ5Nx8yNDcca08eV2Vic29ja2V0HmxKHjAeLTY0Hy0xMDQeY29tbWFuZB90cmlnZ2VyIHRleHQdN1MeTnVtYmVyVG9U"
            "ZXh0HmxKHjAeMTg5Hy0xMjMeHB03UzAfa08w")
HIS_DATA_TITLE = "data block - command Text needs to stay emtpy"
HIS_TEXT_TITLE = "text block - it will trigger if the text starts with the command text"


def _ids(*ids: str):
    left = list(ids)
    return lambda: left.pop(0)


class TestVNyanCopyTexts(unittest.TestCase):
    """The blocks the VNyan tab copies: his exports' shape, with the toolbox's titles."""

    def test_the_text_block_is_his_export_with_another_title(self) -> None:
        made = decode(VNyanCopyTexts(_ids("lJ", "kO", "7S")).text_block("trigger text"))
        title = made.split("\x1e")[1]
        self.assertEqual(decode(HIS_TEXT), made.replace(title, HIS_TEXT_TITLE))

    def test_the_data_block_with_one_key_is_his_export_with_another_title(self) -> None:
        made = decode(VNyanCopyTexts(_ids("TB", "Mh", "QK")).data_block(["key"]))
        title = made.split("\x1e")[1]
        self.assertEqual(decode(HIS_DATA), made.replace(title, HIS_DATA_TITLE))

    def test_the_data_block_gets_one_key_per_value(self) -> None:
        made = decode(VNyanCopyTexts(_ids("Lv", "nn", "zW")).data_block(["key", "key2", " key3 ", ""]))
        # his 3-key export's Dictionary Values settings
        self.assertIn("opts\x1f3\x1fname\x1f\x1fk0\x1fkey\x1fk1\x1fkey2\x1fk2\x1fkey3\x1c", made)
        with self.assertRaisesRegex(ValueError, "Which values"):
            VNyanCopyTexts().data_block(["", " "])

    def test_the_send_block_carries_the_address_and_message(self) -> None:
        address = "ws://127.0.0.1:8850/connections/vnyan/in/default?key=abc"
        made = decode(VNyanCopyTexts(_ids("5K", "lo")).send_block(address, "hello"))
        # his WebSocket Message node: lo, WSMessage, its group, 0, x/y, address/message
        self.assertIn(f"lo\x1eWSMessage\x1e5K\x1e0\x1e-64\x1f-104\x1eaddress\x1f{address}\x1fmessage\x1fhello", made)
        self.assertTrue(made.endswith("\x1c\x1d"))  # no wires

    def test_the_separators_cannot_break_a_block_and_ids_differ(self) -> None:
        made = decode(VNyanCopyTexts(_ids("aa", "aa", "bb", "cc")).text_block(" a\x1eb\x1f "))
        self.assertIn("command\x1fab\x1d", made)
        self.assertEqual(["aa", "bb", "cc"], [made[:2], made.split("\x1c")[1][:2], made.split("\x1d")[1][:2]])
        self.assertTrue(VNyanCopyTexts().text_block("x").startswith(PREFIX))
        with self.assertRaisesRegex(ValueError, "Which Command Text"):
            VNyanCopyTexts().text_block("  ")


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.plugins.listing_addresses import MAIN_LISTING, ListingAddresses, raw_address

RAW = "https://drive.google.com/uc?export=download&id=1DN-I7vMug1yD3Nwk_pH"


class TestListingAddresses(unittest.TestCase):
    def test_a_google_drive_share_link_becomes_its_download_link(self) -> None:
        for link in ("https://drive.google.com/file/d/1DN-I7vMug1yD3Nwk_pH/view?usp=drive_link",
                     "https://drive.google.com/file/d/1DN-I7vMug1yD3Nwk_pH/view",
                     "https://drive.google.com/open?id=1DN-I7vMug1yD3Nwk_pH",
                     "https://drive.google.com/uc?id=1DN-I7vMug1yD3Nwk_pH&export=download", RAW):
            self.assertEqual(raw_address(link), RAW, link)
        self.assertEqual(raw_address("https://example.com/file/d/x/view"), "https://example.com/file/d/x/view")
        addresses = ListingAddresses(self.file)
        addresses.add("https://drive.google.com/file/d/1DN-I7vMug1yD3Nwk_pH/view?usp=drive_link")
        self.assertEqual(addresses.addresses[-1], RAW)

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.file = Path(self._dir.name) / "plugin_listings.txt"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_one_address_per_line_and_notes_stay(self) -> None:
        self.file.write_text("# official\nhttps://a.example/p.toml\n\n# custom list\n  C:/mine.toml  \n",
                             encoding="utf-8")
        addresses = ListingAddresses(self.file)
        self.assertEqual(addresses.addresses, ["https://a.example/p.toml", "C:/mine.toml"])
        addresses.add("https://b.example/p.toml")
        addresses.add("https://b.example/p.toml")  # once only
        addresses.remove("https://a.example/p.toml")
        self.assertEqual(self.file.read_text(encoding="utf-8"),
                         "# official\n\n# custom list\n  C:/mine.toml  \nhttps://b.example/p.toml\n")
        with self.assertRaisesRegex(ValueError, "note"):
            addresses.add("# not an address")

    def test_the_main_one_can_go_and_come_back(self) -> None:
        addresses = ListingAddresses(self.file)
        self.assertEqual(addresses.addresses, [MAIN_LISTING])
        addresses.remove(MAIN_LISTING)
        self.assertEqual(ListingAddresses(self.file).addresses, [])
        addresses.put_main_back()
        self.assertEqual(self.file.read_text(encoding="utf-8"), f"# official\n{MAIN_LISTING}\n")  # under its note again


if __name__ == "__main__":
    unittest.main()

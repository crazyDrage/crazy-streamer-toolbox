import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.plugins.listing_addresses import MAIN_LISTING, ListingAddresses
from streamer_toolbox.plugins.plugin_listing import PluginListing
from streamer_toolbox.plugins.plugin_listings import PluginListings


def listing(name: str, *blocks: str) -> str:
    return "\n".join([f'listing = 1\nname = "{name}"', *blocks]) + "\n"


def block(plugin_id: str, version: str, **more: str) -> str:
    fields = {"id": plugin_id, "name": plugin_id.capitalize(), "version": version,
              "download": f"https://example.com/{plugin_id}-{version}.zip", **more}
    return "\n[[plugin]]\n" + "\n".join(f'{key} = "{value}"' for key, value in fields.items())


class TestPluginListings(unittest.IsolatedAsyncioTestCase):
    """His answers of 2026-11-01 / 11-02: several listing files (a text file, one per line, # notes), each a
    TOML file with one [[plugin]] block per version, every block whole."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.file = self.folder / "plugin_listings.txt"
        self.channel = "release"
        self.served = {MAIN_LISTING: listing("Main", block("jokes", "1.0.0"), block("dice", "2.0.0"))}

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _answer(self, request: httpx.Request) -> httpx.Response:
        text = self.served.get(str(request.url))
        return httpx.Response(200, text=text) if text is not None else httpx.Response(404)

    def listings(self, version: str = "0.3.0", system: str = "windows") -> PluginListings:
        return PluginListings(ListingAddresses(self.file), httpx.MockTransport(self._answer),
                              lambda: self.channel, version, system)

    def test_a_listing_file_is_readable_and_a_broken_block_doesnt_spoil_it(self) -> None:
        parsed = PluginListing.parse(listing("Mine", block("jokes", "1.0.0", about="Tells jokes"),
                                             block("Bad Id", "1"), block("plain", "1.0.0", download="http://x"),
                                             block("odd", "nightly"), '\n[[plugin]]\nid = "half"'), "here")
        self.assertEqual([(p.id, p.about, p.listings) for p in parsed.plugins], [("jokes", "Tells jokes", ("Mine",))])
        self.assertEqual(len(parsed.problems), 4)
        with self.assertRaisesRegex(ValueError, "newer toolbox"):
            PluginListing.parse("listing = 2\n", "here")
        with self.assertRaisesRegex(ValueError, "not TOML"):
            PluginListing.parse('{"listing": 1}', "here")

    def test_a_block_says_what_kind_of_plugin_it_is(self) -> None:
        parsed = PluginListing.parse(listing("Mine", block("jokes", "1.0.0") + '\ntypes = ["Bot", "game", "bot"]',
                                             block("dice", "1.0.0") + '\ntypes = "game"',
                                             block("odd", "1.0.0") + "\ntypes = 3", block("plain", "1.0.0")), "here")
        self.assertEqual([(p.id, p.types) for p in parsed.plugins],
                         [("jokes", ("bot", "game")), ("dice", ("game",)), ("plain", ())])
        self.assertEqual(len(parsed.problems), 1)

    async def test_the_main_listing_comes_filled_in(self) -> None:
        plugins, problems = await self.listings().fetch()
        self.assertEqual(([p.id for p in plugins], problems), (["dice", "jokes"], []))
        self.assertFalse(self.file.exists())  # written at the first change only

    async def test_a_new_version_is_a_block_at_the_end_and_the_newest_that_fits_is_offered(self) -> None:
        self.served[MAIN_LISTING] = listing("Main", block("jokes", "1.0.0"), block("jokes", "1.1.0", toolbox="0.3.0"),
                                            block("jokes", "1.2.0", toolbox="0.4.0"))
        self.assertEqual([p.version for p in (await self.listings("0.3.0").fetch())[0]], ["1.1.0"])
        self.assertEqual([p.version for p in (await self.listings("0.4.0").fetch())[0]], ["1.2.0"])
        too_new = (await self.listings("0.2.0").fetch())[0]  # none fits: the newest, the page says what it needs
        self.assertEqual([p.version for p in too_new], ["1.0.0"])

    async def test_a_broken_version_and_test_versions_are_not_offered_by_default(self) -> None:
        self.served[MAIN_LISTING] = listing("Main", block("jokes", "1.0.0"), block("jokes", "1.1.0", broken="crashes"),
                                            block("jokes", "1.2.0-beta.1"), block("dice", "2.0.0", broken="gone"))
        plugins = (await self.listings().fetch())[0]
        self.assertEqual([(p.id, p.version) for p in plugins], [("jokes", "1.0.0")])
        self.channel = "beta"  # Settings → General → Which versions
        self.assertEqual([p.version for p in (await self.listings().fetch())[0]], ["1.2.0-beta.1"])

    async def test_a_second_listing_counts_too_and_the_newer_version_wins(self) -> None:
        own = self.folder / "own.toml"
        own.write_text(listing("Mine", block("jokes", "1.1.0"), block("dice", "2.0.0")), encoding="utf-8")
        listings = self.listings()
        listings.add(f'"{own}"')  # "Copy as path" quotes it
        plugins = {p.id: p for p in (await listings.fetch())[0]}
        self.assertEqual((plugins["jokes"].version, plugins["jokes"].listings), ("1.1.0", ("Mine",)))
        self.assertEqual(plugins["dice"].listings, ("Main", "Mine"))  # the same version in both
        self.assertEqual(self.file.read_text(encoding="utf-8"), f"# official\n{MAIN_LISTING}\n{own}\n")

    async def test_when_the_main_one_stops_working_the_others_still_count(self) -> None:
        del self.served[MAIN_LISTING]
        self.served["https://mirror.example/plugins.toml"] = listing("Mirror", block("jokes", "1.0.0"))
        listings = self.listings()
        listings.add("https://mirror.example/plugins.toml")
        plugins, problems = await listings.fetch()
        self.assertEqual([p.id for p in plugins], ["jokes"])
        self.assertEqual(len(problems), 1)
        self.assertIn("couldn't be read", problems[0])

    def test_a_block_can_say_whats_new_where_it_runs_and_what_it_needs(self) -> None:
        parsed = PluginListing.parse(listing("Mine", block("jokes", "1.0.0", changes="German jokes") +
                                             '\nos = ["Windows", "linux"]\nneeds = ["dice"]',
                                             block("odd", "1.0.0") + '\nneeds = ["Not An Id"]'), "here")
        self.assertEqual([(p.changes, p.systems, p.needs) for p in parsed.plugins],
                         [("German jokes", ("windows", "linux"), ("dice",))])
        self.assertEqual(len(parsed.problems), 1)

    def test_its_page_is_only_an_https_address(self) -> None:
        """His question of 2026-11-02 ("safe from hacker attacks?"): a javascript: link or one that adds props."""
        parsed = PluginListing.parse(listing("Mine", block("jokes", "1.0.0", page="https://example.com/jokes"),
                                             block("evil", "1.0.0", page="javascript:alert(1)"),
                                             block("props", "1.0.0", page="https://x.com target=_self")), "here")
        self.assertEqual([(p.id, p.page) for p in parsed.plugins], [("jokes", "https://example.com/jokes")])
        self.assertEqual(len(parsed.problems), 2)

    async def test_a_version_for_another_system_is_skipped(self) -> None:
        self.served[MAIN_LISTING] = listing("Main", block("jokes", "1.0.0"),
                                            block("jokes", "1.1.0") + '\nos = ["windows"]',
                                            block("dice", "1.0.0") + '\nos = "windows"')
        on_linux = {p.id: p.version for p in (await self.listings(system="linux").fetch())[0]}
        self.assertEqual(on_linux, {"jokes": "1.0.0", "dice": "1.0.0"})  # dice: none fits, the page says why
        on_windows = {p.id: p.version for p in (await self.listings().fetch())[0]}
        self.assertEqual(on_windows, {"jokes": "1.1.0", "dice": "1.0.0"})

    async def test_the_main_listings_block_counts_when_another_has_the_same_version(self) -> None:
        own = self.folder / "own.toml"
        own.write_text(listing("Mine", block("jokes", "1.0.0", download="https://evil.example/j.zip")),
                       encoding="utf-8")
        self.served[MAIN_LISTING] = listing("Main", block("jokes", "1.0.0"))
        listings = self.listings()
        listings.add(str(own))
        listings.remove(MAIN_LISTING)
        listings.put_main_back()  # the main one after the own one in the file: its block still counts
        plugin = (await listings.fetch())[0][0]
        self.assertEqual((plugin.download, plugin.official), ("https://example.com/jokes-1.0.0.zip", True))

    async def test_the_other_versions_to_go_back_to(self) -> None:
        self.served[MAIN_LISTING] = listing("Main", block("jokes", "1.0.0"), block("jokes", "1.1.0", broken="x"),
                                            block("jokes", "1.2.0"), block("jokes", "1.3.0", toolbox="9.0.0"),
                                            block("jokes", "1.4.0"))
        listings = self.listings()
        await listings.fetch()
        self.assertEqual([p.version for p in listings.others("jokes", "1.4.0")], ["1.2.0", "1.0.0"])
        self.assertEqual(listings.others("dice", "1.0.0"), [])


if __name__ == "__main__":
    unittest.main()

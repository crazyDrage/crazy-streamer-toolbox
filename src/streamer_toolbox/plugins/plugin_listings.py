import asyncio
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import httpx

from streamer_toolbox.core.app_version import APP_VERSION, channel_takes, is_newer, version_numbers
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.web.web_error import web_error
from streamer_toolbox.plugins.listed_plugin import ListedPlugin
from streamer_toolbox.plugins.listing_addresses import MAIN_LISTING, ListingAddresses, raw_address
from streamer_toolbox.plugins.plugin_listing import PluginListing
from streamer_toolbox.plugins.plugin_systems import runs_here, this_system


class PluginListings:
    """The listing files the Plugins page shows plugins from (his answer of 2026-11-01: "a setting for it,
    where we can set multiple listing files ... a custom listing file if the main one stops working"). Where
    they are is kept in ListingAddresses (a text file, one address per line); each is a web address (http or
    https) or a file on this PC.

    fetch() reads them all at once and offers one version per plugin: of the versions every listing has
    (several per plugin: one [[plugin]] block each), not broken and of a stage "Which versions" takes
    (`channel`, the same setting as the toolbox's update), the newest one this toolbox is new enough for and that
    runs on this system; when there is none, the newest one (the page says what it needs). A listing that can't
    be read is said in the problems; the others still count.

    The main listing's versions are `official`. The same version in the main listing and another one: the main
    one's block counts (its download), so another listing can't slip its own zip in under that version.
    `others(id)`: the other versions that could be installed instead (going back after a bad update)."""

    def __init__(self, addresses: ListingAddresses, transport: httpx.AsyncBaseTransport | None = None,
                 channel: Callable[[], str] = lambda: "release", version: str = APP_VERSION,
                 system: str | None = None) -> None:
        self._addresses = addresses
        self._transport = transport
        self._channel = channel
        self._version = version
        self._system = system or this_system()
        self._versions: dict[str, list[ListedPlugin]] = {}  # every version read, per plugin id

    @property
    def addresses(self) -> list[str]:
        return self._addresses.addresses

    def add(self, address: str) -> None:
        self._addresses.add(address)

    def remove(self, address: str) -> None:
        self._addresses.remove(address)

    def put_main_back(self) -> None:
        self._addresses.put_main_back()

    async def fetch(self) -> tuple[list[ListedPlugin], list[str]]:
        """The version offered of every listed plugin (A-Z by name) and what went wrong, one line each."""
        addresses = self.addresses
        results = await asyncio.gather(*(self._read(a) for a in addresses), return_exceptions=True)
        versions: dict[str, list[ListedPlugin]] = {}
        problems = []
        for address, result in zip(addresses, results):
            if isinstance(result, Exception):
                problems.append(f"{address}: {result}")
                continue
            problems += [f"{result.name}: {p}" for p in result.problems]
            for plugin in result.plugins:
                plugin = replace(plugin, official=address == MAIN_LISTING)
                versions.setdefault(plugin.id, []).append(plugin)
        self._versions = versions
        offered = [plugin for plugin in map(self._pick, versions.values()) if plugin is not None]
        return sorted(offered, key=lambda p: p.name.casefold()), problems

    def others(self, plugin_id: str, but: str) -> list[ListedPlugin]:
        """The versions of a plugin that could be installed besides `but` (the one offered or installed), newest
        first: not broken, of a stage "Which versions" takes, for this toolbox and system."""
        usable = [p for p in self._usable(self._versions.get(plugin_id, [])) if self._fits(p)]
        found = {}
        for plugin in sorted(usable, key=lambda p: not p.official):  # the main listing's block first
            found.setdefault(version_numbers(plugin.version), plugin)
        found.pop(version_numbers(but), None)
        return [found[numbers] for numbers in sorted(found, reverse=True)]

    def _usable(self, versions: list[ListedPlugin]) -> list[ListedPlugin]:
        return [p for p in versions if not p.broken and channel_takes(self._channel(), p.version)]

    def _fits(self, plugin: ListedPlugin) -> bool:
        return ((not plugin.toolbox or not is_newer(plugin.toolbox, self._version))
                and runs_here(plugin.systems, self._system))

    def _pick(self, versions: list[ListedPlugin]) -> ListedPlugin | None:
        usable = self._usable(versions)
        if not usable:
            return None
        fits = [p for p in usable if self._fits(p)]
        best = max(fits or usable, key=lambda p: version_numbers(p.version))
        same = [p for p in usable if version_numbers(p.version) == version_numbers(best.version)]
        best = next((p for p in same if p.official), best)
        return replace(best, listings=tuple(dict.fromkeys(name for p in same for name in p.listings)))

    async def _read(self, address: str) -> PluginListing:
        if address.startswith(("http://", "https://")):
            async with web_client(self._transport, timeout=15, follow_redirects=True) as client:
                try:
                    answer = await client.get(raw_address(address))  # also a share link typed into the file
                    answer.raise_for_status()
                except httpx.HTTPError as e:
                    raise RuntimeError(f"couldn't be read ({web_error(e)})") from None
                text = answer.text
        else:
            try:
                text = Path(address).read_text(encoding="utf-8")
            except OSError as e:
                raise RuntimeError(f"couldn't be read ({e.strerror or e})") from None
        return PluginListing.parse(text, address)

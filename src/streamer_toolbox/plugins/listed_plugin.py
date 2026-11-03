from dataclasses import dataclass


@dataclass(frozen=True)
class ListedPlugin:
    """One version of a plugin in a plugin listing (a `[[plugin]]` block, PluginListing): who made it, what it
    does, the oldest toolbox version it works with, and where the toolbox downloads it (a zip with the plugin
    folder). `sha256`: when the listing gives it, the download must match it. `listings`: the names of the
    listings that have this version. `broken`: why this version is not offered any more ("" = it is). `types`:
    what kind of plugin it is (plugin_types.PLUGIN_TYPES ids, as the listing wrote them). `changes`: what's new
    in this version. `systems`: the systems it runs on (plugin_systems; empty = all). `needs`: ids of plugins
    that must be installed first. `official`: it comes from the main listing (the one he checks)."""

    id: str
    name: str
    version: str
    download: str
    about: str = ""
    author: str = ""
    toolbox: str = ""
    page: str = ""
    sha256: str = ""
    listings: tuple[str, ...] = ()
    broken: str = ""
    types: tuple[str, ...] = ()
    changes: str = ""
    systems: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    official: bool = False

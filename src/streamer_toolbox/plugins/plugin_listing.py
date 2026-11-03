import tomllib
from dataclasses import dataclass

from streamer_toolbox.core.app_version import version_numbers
from streamer_toolbox.plugins.listed_plugin import ListedPlugin
from streamer_toolbox.plugins.plugin_manifest import ID_PATTERN

FORMAT = 1  # "listing": the file's format number (next release plan, part 3: every file says its version)
NEEDED = ("id", "name", "version", "download")
MORE = ("about", "author", "toolbox", "page", "sha256", "broken", "changes")


@dataclass(frozen=True)
class PluginListing:
    """A plugin listing file (his answers of 2026-11-02: easy to add to, several versions of a plugin, every
    block written whole). TOML, one `[[plugin]]` block per version of a plugin; a new version is a new block at
    the end, the old blocks stay:

        listing = 1
        name = "crazy-streamer-toolbox plugins"

        [[plugin]]
        id = "jokes"
        name = "Jokes"
        version = "1.2.0"
        download = "https://github.com/someone/jokes/releases/download/v1.2.0/jokes.zip"
        about = "A box that tells a joke in chat"     # the rest is optional
        author = "someone"
        page = "https://github.com/someone/jokes"
        toolbox = "0.3.0"                             # the oldest toolbox it works with
        sha256 = "..."                                # the download must match it
        broken = "why"                                # this version is not offered any more
        types = ["bot", "game"]                       # what kind of plugin (plugin_types; one or several)
        changes = "Jokes in German too"               # what's new in this version
        os = ["windows"]                              # only runs there (plugin_systems; none = everywhere)
        needs = ["dice"]                              # plugins that must be installed first

    id, name, version and download are needed in every block; download must be https. A block that breaks
    these is left out and said in `problems`; the rest of the file still counts. Which version is offered is
    PluginListings' choice."""

    name: str
    plugins: tuple[ListedPlugin, ...]  # every block: the same plugin can be in it more than once
    problems: tuple[str, ...] = ()

    @classmethod
    def parse(cls, text: str, address: str) -> "PluginListing":
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"not a listing file (not TOML: {e})") from None
        if "listing" not in data:
            raise ValueError("not a listing file (it has no \"listing = 1\" line)")
        if not isinstance(data["listing"], int) or data["listing"] > FORMAT:
            raise ValueError(f"made for a newer toolbox (listing format {data['listing']!r})")
        blocks = data.get("plugin", [])
        if not isinstance(blocks, list):
            raise ValueError("not a listing file (its plugins must be [[plugin]] blocks)")
        name = str(data.get("name") or address)
        plugins, problems = [], []
        for block in blocks:
            try:
                plugins.append(_plugin(block, name))
            except ValueError as e:
                problems.append(str(e))
        return cls(name, tuple(plugins), tuple(problems))


def _plugin(block: object, listing: str) -> ListedPlugin:
    if not isinstance(block, dict):
        raise ValueError(f"a block that isn't a plugin: {block!r}")
    missing = [key for key in NEEDED if not str(block.get(key) or "").strip()]
    if missing:
        raise ValueError(f"{block.get('id') or block.get('name') or 'a plugin'}: missing {', '.join(missing)}")
    plugin_id = str(block["id"]).strip()
    if not ID_PATTERN.match(plugin_id):
        raise ValueError(f"{plugin_id}: an id is lowercase letters, digits and _")
    version = str(block["version"]).strip()
    if not version_numbers(version):
        raise ValueError(f"{plugin_id}: {version!r} isn't a version (like 1.2.0 or 1.3.0-beta.1)")
    download = str(block["download"]).strip()
    if not download.startswith("https://"):
        raise ValueError(f"{plugin_id} {version}: its download must be an https address")
    text = {key: str(block.get(key) or "").strip() for key in MORE}
    which = f"{plugin_id} {version}"
    if text["page"] and not (text["page"].startswith("https://") and not any(c.isspace() for c in text["page"])):
        raise ValueError(f"{which}: its page must be an https address without spaces")  # no javascript: links
    needs = _words(block, "needs", which, '["dice"]')
    bad = [n for n in needs if not ID_PATTERN.match(n)]
    if bad:
        raise ValueError(f"{which}: needs is a list of plugin ids ({', '.join(bad)} isn't one)")
    return ListedPlugin(plugin_id, str(block["name"]).strip(), version, download, text["about"], text["author"],
                        text["toolbox"], text["page"], text["sha256"].lower(), (listing,), text["broken"],
                        _words(block, "types", which, '["bot", "game"]'), text["changes"],
                        _words(block, "os", which, '["windows", "linux"]'), needs)


def _words(block: dict, key: str, which: str, like: str) -> tuple[str, ...]:
    """A list of words (`types = ["bot", "game"]`, or one: `types = "game"`), lowercase; unknown words are kept
    (a newer list)."""
    value = block.get(key, [])
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
        raise ValueError(f"{which}: {key} is a list of words, like {key} = {like}")
    return tuple(dict.fromkeys(t.strip().lower() for t in value if t.strip()))

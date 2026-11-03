"""The kinds of plugin a listing can say a plugin is (his ask of 2026-11-02: "we need plugin types, too ... make
it sort-able like streaming platform, triggers, bots, games ... because it could be hard if we have a lot of
plugins"). A plugin can be of several (a Discord bot that adds triggers). The ids are what a listing writes
(`types = ["bot", "trigger"]`); the order here is the order on Get plugins.

A type this toolbox doesn't know gets its own chip, named after its id (`chat_games` → "Chat games"): the
form's "Other" field makes new types, and his tick ("checked") adds them to the form for the next person
(his ask of 2026-11-02: "Is there an option to extend that selection automatically?")."""

PLUGIN_TYPES = {
    "platform": "Streaming platforms",
    "trigger": "Triggers",
    "bot": "Bots",
    "game": "Games",
    "avatar": "VTuber and avatars",
    "audio": "Audio",
    "overlay": "Overlays and alerts",
    "tool": "Tools",
    "other": "Other",
}
OTHER = "other"


def plugin_types(types: tuple[str, ...]) -> tuple[str, ...]:
    """The plugin's types as Get plugins sorts by them; none at all is "other"."""
    return tuple(dict.fromkeys(types)) or (OTHER,)


def type_label(type_id: str) -> str:
    return PLUGIN_TYPES.get(type_id) or type_id.replace("_", " ").strip().capitalize() or PLUGIN_TYPES[OTHER]


def type_order(type_ids) -> list[str]:
    """The known types in their order, then new ones by name, "Other" last."""
    known = [t for t in PLUGIN_TYPES if t in type_ids and t != OTHER]
    new = sorted((t for t in set(type_ids) if t not in PLUGIN_TYPES), key=type_label)
    return known + new + ([OTHER] if OTHER in type_ids else [])

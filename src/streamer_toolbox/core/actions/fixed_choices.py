from collections.abc import Collection, Mapping

from streamer_toolbox.core.actions.registered_action import OptionsProvider


def fixed_choices(choices: Collection[str] | Mapping[str, str]) -> OptionsProvider:
    """A picker with a list that never changes, for a box's `options`: fixed_choices(["+", "-"]), or value →
    label: fixed_choices({"restart": "Start the wait over"})."""
    async def provider() -> list[str] | dict[str, str]:
        return dict(choices) if isinstance(choices, Mapping) else list(choices)
    return provider

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.actions.registered_action import (ActionHandler, FillProvider, HintProvider,
                                                             LightProvider, OptionsProvider, RegisteredAction)
from streamer_toolbox.core.actions.switched_off_error import SwitchedOffError
from streamer_toolbox.core.actions.unknown_action_error import UnknownActionError

if TYPE_CHECKING:
    from streamer_toolbox.core.interfaces.box import Box


class ActionRegistry:
    """Every action the toolbox can run, by name: from the core, from plugins, for SAMMI, Kit and the GUI."""

    def __init__(self) -> None:
        self._actions: dict[str, RegisteredAction] = {}
        self._parked: frozenset[str] = frozenset()
        self._why_not: Callable[[str], str] = lambda name: ""
        self._sections: Callable[[], dict[str, str]] = dict

    def guard(self, why_not: Callable[[str], str]) -> None:
        """why_not(action name) is asked before every run: a text (why it can't run now, e.g. its plugin is
        switched off) stops it with that text, "" lets it run."""
        self._why_not = why_not

    def sort_into(self, sections: Callable[[], dict[str, str]]) -> None:
        """sections() = box category → SERVICES or PLUGINS (the connected programs, the plugins); every other
        category is UTILS, the toolbox's own (the Add box window's three groups, his round 63)."""
        self._sections = sections

    def section(self, category: str) -> str:
        return self._sections().get(category, UTILS)

    def park(self, names: Iterable[str]) -> None:
        """Leaves these actions out of all() from now on (the parked boxes, see wip_boxes.py). They can still
        be run and looked up by name, so a flow that has one keeps working."""
        self._parked = frozenset(names)

    def add(self, name: str, handler: ActionHandler, description: str = "", label: str = "",
            options: dict[str, OptionsProvider] | None = None, capture: str = "", group: str = "",
            ports: tuple[str, ...] = (), flow_only: bool = False, join: bool = False,
            live: bool = False, outputs: dict[str, str] | None = None,
            port_fields: str = "", labels: dict[str, str] | None = None,
            hints: dict[str, str] | None = None, editors: dict[str, str] | None = None,
            entries: tuple[str, ...] = (), fills: dict[str, FillProvider] | None = None,
            live_hints: dict[str, HintProvider] | None = None,
            files: dict[str, tuple[str, ...]] | None = None, colors: tuple[str, ...] = (),
            many: dict[str, OptionsProvider] | None = None,
            lights: dict[str, LightProvider] | None = None,
            shown: dict[str, tuple[str, tuple[str, ...]]] | None = None,
            typed: tuple[str, ...] = (), value_lines: str = "", data_only: bool = False,
            entry_fields: str = "", named_lines: bool = False, toggles: tuple[str, ...] = (),
            offered: bool = True, ends_flow: bool = False, gives_back: str = "", once_per_flow: bool = False,
            retrigger: str = "", variable_fields: tuple[str, ...] = (),
            keys_of: str = "", alongside: str = "") -> None:
        """See RegisteredAction for what options, capture, group, ports, flow_only, join, live, outputs,
        port_fields, labels, hints, editors, entries, fills, live_hints, files, colors, many,
        lights, shown, typed, value_lines, data_only, entry_fields, named_lines, toggles, offered, ends_flow, gives_back,
        once_per_flow, retrigger, variable_fields, keys_of and alongside mean."""
        if name in self._actions:
            raise ValueError(f"action {name!r} is already registered")
        self._actions[name] = RegisteredAction(name, handler, description, label, dict(options or {}), capture,
                                               group, tuple(ports), flow_only, join, live,
                                               dict(outputs or {}), port_fields,
                                               dict(labels or {}), dict(hints or {}), dict(editors or {}),
                                               tuple(entries), dict(fills or {}), dict(live_hints or {}),
                                               {k: tuple(v) for k, v in (files or {}).items()},
                                               tuple(colors), dict(many or {}), dict(lights or {}),
                                               {k: (c, tuple(v)) for k, (c, v) in (shown or {}).items()},
                                               tuple(typed), value_lines, data_only, entry_fields,
                                               named_lines, tuple(toggles), offered, ends_flow, gives_back,
                                               once_per_flow, retrigger, tuple(variable_fields), keys_of,
                                               alongside)

    def add_box(self, box: "Box", owner: str) -> str:
        """A Box class's box as "<owner>.<name>" (owner: a connection's or plugin's id, or "logic", ...).
        Returns the full name."""
        if not box.name:
            raise ValueError(f"{type(box).__name__} needs a name")
        name = f"{owner}.{box.name}"
        self.add(name, box.run, box.help, box.label, **box.box_options())
        return name

    def mark(self, name: str, is_tested: bool, is_understandable: bool, is_usable: bool) -> None:
        """Sets his three checks on a box (from the test record); unknown names are ignored."""
        if name in self._actions:
            self._actions[name] = replace(self._actions[name], is_tested=is_tested,
                                          is_understandable=is_understandable, is_usable=is_usable)

    def remove(self, name: str) -> None:
        """Drops an action (an edited or deleted flow); unknown names are ignored."""
        self._actions.pop(name, None)

    def all(self, include_flow_only: bool = False) -> list[RegisteredAction]:
        """Every action by name; the flow-only ones (If, Wait, ...) only when asked for (the flow editor).
        Parked ones are never in it."""
        return sorted((a for a in self._actions.values()
                       if (include_flow_only or not a.flow_only) and a.name not in self._parked),
                      key=lambda a: a.name)

    def live(self) -> list[RegisteredAction]:
        """The actions a box field can read directly (Live value), e.g. the loaded VTS model."""
        return [a for a in self.all(include_flow_only=True) if a.live]

    def get(self, name: str) -> RegisteredAction:
        action = self._actions.get(name)
        if action is None:
            raise UnknownActionError(name)
        return action

    def __contains__(self, name: str) -> bool:
        return name in self._actions

    async def run(self, action_name: str, /, **params: Any) -> Any:
        # positional-only, so an action may have its own "name" parameter
        action = self.get(action_name)
        why_not = self._why_not(action_name)
        if why_not:
            raise SwitchedOffError(why_not)
        return await action.handler(**params)


UTILS, SERVICES, PLUGINS = "Utils", "Services", "Plugins"
SECTIONS = (UTILS, SERVICES, PLUGINS)  # in this order in the Add box window

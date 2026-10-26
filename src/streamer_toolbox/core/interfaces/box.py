from abc import ABC, abstractmethod
from dataclasses import fields
from typing import Any, Optional

from streamer_toolbox.core.actions.registered_action import (FillProvider, HintProvider, LightProvider,
                                                             OptionsProvider, RegisteredAction)
from streamer_toolbox.core.flows.box_signals import BoxSignals
from streamer_toolbox.core.flows.retrigger import Retrigger, current_retrigger

# what RegisteredAction holds besides the name, the handler, the texts and his three checks: every one is an
# attribute below (tests/plugins/test_plugin_parity.py keeps it so)
OPTIONS = tuple(f.name for f in fields(RegisteredAction)
                if f.name not in {"name", "handler", "description", "label", "is_tested", "is_understandable",
                                  "is_usable"})


class Box(ABC):
    """A box in the flow editor (also a button on Live, in the SAMMI deck and POST /action/<name>).

    Write one class per box: set what it needs as class attributes, and `run` is what it does. The parameters of
    `run` are the box's fields; a default makes a field optional; the type (str, int, float, bool) decides the
    input. What `run` returns is the box's result; return a dict and name its keys in `outputs`. To refuse,
    raise with words the streamer understands.

        class Shout(Box):
            name = "shout"
            label = "Shout"
            help = "Makes a text loud"
            outputs = {"text": "text"}

            async def run(self, text: str = "hello") -> dict[str, str]:
                return {"text": text.upper() + "!"}

    An option that needs the box's own data (a picker that asks the program) is set in __init__:
    `self.options = {"color": self.color_names}`. Set the attributes, don't change the dicts in place: they are
    shared by every box that doesn't set its own.

    Its full name is "<owner>.<name>": the plugin's or the connection's id goes in front by itself."""

    name: str = ""
    label: str = ""   # the box's title; empty: the name with spaces
    help: str = ""    # one line under its title: what it does, in the streamer's words

    # where it is and how it looks
    group: str = ""                                          # its sub list in the Add box window
    hints: dict[str, str] = {}                               # one help line per field
    labels: dict[str, str] = {}                              # another name per field
    offered: bool = True                                     # False: not in the Add box window
    flow_only: bool = False                                  # only in flows: not on Live, SAMMI, the API
    live: bool = False                                       # a reading box without fields: a Live value

    # its fields
    options: dict[str, OptionsProvider] = {}                 # a picker per field
    many: dict[str, OptionsProvider] = {}                    # a field that takes several of a list
    lights: dict[str, LightProvider] = {}                    # with many: light the one under the mouse
    files: dict[str, tuple[str, ...]] = {}                   # a field that picks a file (its endings)
    colors: tuple[str, ...] = ()                             # a field with a colour picker
    editors: dict[str, str] = {}                             # a field with its own window (a FieldEditor)
    shown: dict[str, tuple[str, tuple[str, ...]]] = {}       # a field shown only for some values of another
    typed: tuple[str, ...] = ()                              # fields that keep any kind of value
    fills: dict[str, FillProvider] = {}                      # setting a field fills others
    live_hints: dict[str, HintProvider] = {}                 # a hint worked out from the box's values
    variable_fields: tuple[str, ...] = ()                    # fields that hold a variable's name
    capture: str = ""                                        # an action that saves the program's state

    # its dots
    outputs: dict[str, str] = {}                             # the keys its result always has: data dots
    keys_of: str = ""                                       # a dot per key of what's wired into this field
    ports: tuple[str, ...] = ()                              # several run outputs (then / else)
    port_fields: str = ""                                    # a field it can have any number of, each a run output
    entries: tuple[str, ...] = ()                            # extra run dots on the left (a Loop's stop)
    toggles: tuple[str, ...] = ()                            # entries that start it when it isn't running
    entry_fields: str = ""                                   # a field it can have any number of, each a run dot
    value_lines: str = ""                                    # lines of name + value, each a data dot (Value)
    named_lines: bool = False                                # lines he names, handed over as **values (End)
    data_only: bool = False                                  # no run dots: runs when a wired field needs it
    join: bool = False                                       # runs once every run wire into it arrived

    # what it does to its flow
    ends_flow: bool = False                                  # the flow's box in another flow goes on (End)
    gives_back: str = ""                                     # the field naming what the flow gives back
    once_per_flow: bool = False                              # a flow takes one of it
    retrigger: str = ""                                      # the field saying what a new start does (Wait)
    alongside: str = ""                                      # the field that lets each run have its own (Loop)

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """What the box does. Give it your own parameters: they are the box's fields. It may also be an async
        generator that yields port names one after the other (a Loop's "each", ..., "done")."""

    def box_options(self) -> dict[str, Any]:
        """Every option above, as ActionRegistry.add takes them."""
        return {option: getattr(self, option) for option in OPTIONS}

    @staticmethod
    def signals() -> Optional[BoxSignals]:
        """While it runs in a flow: what arrived at its `entries` (.has("stop"), await .wait_for(seconds,
        "stop")). None outside a flow (Test box, API)."""
        return BoxSignals.current()

    @staticmethod
    def started_again() -> Optional[Retrigger]:
        """In a box with `retrigger`: the run's Retrigger, so a new start of the flow stretches its wait
        (await .wait(seconds, mode)) like the Wait box. None when nothing asks for it."""
        return current_retrigger.get()

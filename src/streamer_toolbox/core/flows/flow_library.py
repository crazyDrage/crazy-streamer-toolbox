import re
import tomllib
from dataclasses import replace
from pathlib import Path

import tomlkit

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_store import NAME, FlowStore
from streamer_toolbox.core.flows.variable_renamer import VariableRenamer


class FlowLibrary:
    """The flows and templates the toolbox knows. Keeps the flow.<name> actions in step with the files when a
    flow is created, edited, renamed or deleted, so no restart is needed."""

    def __init__(self, store: FlowStore, templates: FlowStore, runner: FlowRunner, actions: ActionRegistry) -> None:
        self._store = store
        self._templates = templates
        self._runner = runner
        self._actions = actions
        self._flows: dict[str, Flow] = {}

    @property
    def folder(self) -> Path:
        return self._store.folder

    def load(self) -> None:
        for flow in self._store.all():
            self._register(flow)

    def all(self) -> list[Flow]:
        return sorted(self._flows.values(), key=lambda f: f.label.casefold())

    def get(self, name: str) -> Flow | None:
        return self._flows.get(name)

    def folders(self) -> list[str]:
        """The folders the flows are in, A-Z (a folder exists while a flow is in it)."""
        return sorted({f.folder for f in self._flows.values() if f.folder}, key=str.casefold)

    def move(self, name: str, folder: str) -> None:
        """Puts a flow in a folder ("" = none). Only the Flows page's sorting: its file and action stay."""
        self.save(replace(self._flows[name], folder=folder.strip()))

    def rename_folder(self, old: str, new: str) -> None:
        """Every flow in old goes to new ("" = no folder: the folder is gone)."""
        for flow in [f for f in self._flows.values() if f.folder == old]:
            self.move(flow.name, new)

    def rename_reward(self, reward_id: str, title: str) -> list[str]:
        """A reward got a new title on Twitch: the redeem triggers saved with its id show the new name. Gives the
        flows that changed."""
        changed = []
        for flow in list(self._flows.values()):
            triggers = tuple(
                FlowTrigger(t.kind, {**t.match, "reward": title})
                if t.match.get("reward_id") == reward_id and t.match.get("reward") != title else t
                for t in flow.triggers)
            if triggers != flow.triggers:
                self.save(replace(flow, triggers=triggers))
                changed.append(flow.name)
        return changed

    def rename_custom_trigger(self, old: str, new: str) -> list[str]:
        """A custom trigger got a new name: flows listening to it listen to the new one. Gives the flows changed."""
        changed = []
        for flow in list(self._flows.values()):
            triggers = tuple(
                FlowTrigger(t.kind, {**t.match, "trigger": new})
                if t.kind == "custom" and str(t.match.get("trigger", "")).casefold() == old.casefold() else t
                for t in flow.triggers)
            if triggers != flow.triggers:
                self.save(replace(flow, triggers=triggers))
                changed.append(flow.name)
        return changed

    def templates(self) -> list[Flow]:
        return self._templates.all()

    def save(self, flow: Flow, old_name: str | None = None) -> None:
        """Writes the flow and makes its action current. old_name: its name before a rename."""
        self._store.save(flow)
        if old_name and old_name != flow.name:
            self.delete(old_name)
        self._register(flow)

    def delete(self, name: str) -> None:
        self._store.delete(name)
        flow = self._flows.pop(name, None)
        if flow is not None:
            self._actions.remove(flow.action_name)

    def export_text(self, name: str) -> str:
        """The flow as its .toml file text, to download and keep or share."""
        return tomlkit.dumps(FlowStore.to_data(self._flows[name]))

    def import_text(self, text: str, file_name: str = "") -> Flow:
        """Adds a flow from an exported .toml file, under a free name. A flow whose label is taken already comes in
        as "<label> (imported)" without its triggers, so a redeem doesn't start both."""
        try:
            data = tomllib.loads(text)
            if "nodes" not in data and "steps" not in data:
                raise ValueError("it has no boxes")
            flow = FlowStore.parse("imported", data)
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"{file_name or 'this file'} is not a flow file: {e}") from None
        label = flow.label if "label" in data else Path(file_name).stem or "Imported flow"
        if any(f.label.casefold() == label.casefold() for f in self._flows.values()):
            flow = replace(flow, triggers=())
            label = f"{label} (imported)"
        flow = replace(flow, name=self.free_name(label), label=label)
        self.save(flow)
        return flow

    def folder_pack(self, folder: str) -> FlowPack:
        """A folder's flows as one file to give away (FlowPack.to_text), A-Z. Flows from elsewhere that they use
        as boxes come along (after them, with their own folder), or those boxes would be empty for the receiver."""
        pack = FlowPack(folder, tuple(f for f in self.all() if f.folder == folder))
        while more := [self._flows[name] for name in pack.needs() if name in self._flows]:
            pack = FlowPack(folder, pack.flows + tuple(more))
        return pack

    def import_file(self, text: str, file_name: str = "") -> list[Flow]:
        """Adds what an exported file holds: one flow, or a folder of flows (import_text's rules for each)."""
        try:
            data = tomllib.loads(text)
        except ValueError as e:
            raise ValueError(f"{file_name or 'this file'} is not a flow file: {e}") from None
        if not FlowPack.is_pack(data):
            return [self.import_text(text, file_name)]
        try:
            pack = FlowPack.from_data(data)
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"{file_name or 'this file'} is not a file with flows: {e}") from None
        return self._import_pack(pack)

    def _import_pack(self, pack: FlowPack) -> list[Flow]:
        """Every flow under its file name (a free one where that is taken), in the pack's folder. A flow whose label is taken comes in as
        "<label> (imported)" without its triggers; boxes that run a flow of the pack run the imported one."""
        names: dict[str, str] = {}
        labels: dict[str, str] = {}
        for flow in pack.flows:
            taken = any(f.label.casefold() == flow.label.casefold() for f in self._flows.values())
            labels[flow.name] = f"{flow.label} (imported)" if taken else flow.label
            used = set(names.values())
            keeps = NAME.fullmatch(flow.name) and flow.name not in used and self.free_name(flow.name) == flow.name
            # its own file name where that is free: buttons, SAMMI and other folders' flows know it by that
            names[flow.name] = flow.name if keeps else self.free_name(labels[flow.name], used)
        imported = []
        for old, flow in zip(names, pack.renamed(names).flows):
            label = labels[old]
            flow = replace(flow, label=label, triggers=flow.triggers if label == flow.label else ())
            self.save(flow)
            imported.append(flow)
        return imported

    def rename_variable(self, old: str, new: str) -> list[str]:
        """A variable got a new name: every flow and template that uses it is changed and saved. Gives back the
        labels of the ones that changed."""
        renamer = VariableRenamer(old, new)
        changed = []
        for flow in list(self._flows.values()):
            renamed = renamer.flow(flow)
            if renamed is not None:
                self.save(renamed)
                changed.append(flow.label)
        for template in self._templates.all():
            renamed = renamer.flow(template)
            if renamed is not None:
                self._templates.save(renamed)
                changed.append(f"{template.label} (template)")
        return changed

    def save_template(self, flow: Flow) -> None:
        self._templates.save(flow)

    def delete_template(self, name: str) -> None:
        self._templates.delete(name)

    def free_name(self, label: str, taken: set[str] = frozenset()) -> str:
        """A file name from a label that no flow uses yet ("Just Chatting" → just_chatting_2)."""
        base = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_") or "flow"
        name, n = base, 2
        while name in self._flows or name in taken or self._store.exists(name):
            name, n = f"{base}_{n}", n + 1
        return name

    def free_template_name(self, label: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_") or "template"
        name, n = base, 2
        while self._templates.exists(name):
            name, n = f"{base}_{n}", n + 1
        return name

    def _register(self, flow: Flow) -> None:
        old = self._flows.get(flow.name)
        if old is not None:
            self._actions.remove(old.action_name)
        self._flows[flow.name] = flow
        self._runner.register(flow)

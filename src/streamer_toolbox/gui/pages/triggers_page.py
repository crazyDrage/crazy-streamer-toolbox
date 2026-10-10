from dataclasses import replace

from nicegui import ui

from streamer_toolbox.core.flows.role_match import ROLE_KEYS, roles_match, roles_of, roles_text
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.triggers.custom_trigger import CUSTOM, CustomTrigger
from streamer_toolbox.core.triggers.custom_trigger_actions import CustomTriggerActions
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore
from streamer_toolbox.gui.components.source_dialog import RewardChoices, SourceDialog, source_kinds

FOLDER = "Triggers"  # where Make a flow puts a new flow


class TriggersPage:
    """His custom triggers: what fires each one (its sources: a redeem, a chat command, a VTS hotkey, a key, ...;
    or the Fire custom trigger action from SAMMI, Kit, a flow) and which flows it starts. One flow per trigger
    serves every platform (Twitch now, YouTube later); the flow can check platform."""

    def __init__(self, store: CustomTriggerStore, flows: FlowLibrary, fire: CustomTriggerActions,
                 rewards: RewardChoices) -> None:
        self._store = store
        self._flows = flows
        self._fire = fire
        self._rewards = rewards

    @ui.refreshable_method
    def build(self) -> None:
        with ui.row().classes("items-center w-full gap-2"):
            ui.button("New trigger", icon="add", on_click=self._new).props("unelevated no-caps")
            ui.label("A custom trigger is fired by its sources (or by Fire custom trigger from SAMMI, Kit, a flow) "
                     "and starts every flow that listens to it. The flow gets trigger, platform, source, user, "
                     "input and the source's own fields.").classes("text-xs opacity-60 flex-1")
        triggers = self._store.all()
        if not triggers:
            ui.label("No custom triggers yet: New trigger makes one.").classes("opacity-70")
        with ui.element("div").classes("grid gap-3 w-full lg:grid-cols-2 items-start"):
            for trigger in triggers:
                self._card(trigger)

    def _card(self, trigger: CustomTrigger) -> None:
        with ui.card().classes("w-full gap-2"):
            with ui.row().classes("items-center w-full gap-2"):
                ui.icon("bolt").classes("text-xl text-warning")
                ui.label(trigger.name).classes("text-lg font-semibold")
                ui.space()
                ui.button("Fire now", icon="play_arrow", on_click=lambda: self._test(trigger)) \
                    .props("flat dense no-caps").tooltip("Fires it with platform = test: the flows really run")
                with ui.button(icon="more_vert").props("flat round dense"):
                    with ui.menu():
                        ui.menu_item("Rename / description", on_click=lambda: self._rename(trigger))
                        ui.menu_item("Delete", on_click=lambda: self._delete(trigger))
            if trigger.description:
                ui.label(trigger.description).classes("text-sm opacity-80")
            ui.label("Fired by").classes("text-xs font-semibold uppercase opacity-70")
            with ui.row().classes("gap-1 items-center"):
                for source in trigger.sources:
                    ui.chip(_source_text(source), icon="input", removable=True,
                            on_value_change=lambda e, s=source: None if e.value else self._remove(trigger, s)) \
                        .props("dense outline")
                ui.button("Source", icon="add", on_click=lambda: self._add_source(trigger)) \
                    .props("flat dense no-caps size=sm")
                if not trigger.sources:
                    ui.label("only Fire custom trigger so far").classes("text-xs opacity-60")
            ui.label("Starts").classes("text-xs font-semibold uppercase opacity-70")
            with ui.row().classes("gap-1 items-center"):
                for flow in self._listening(trigger):
                    ui.chip(flow.label, icon="account_tree",
                            on_click=lambda f=flow: ui.navigate.to(f"/flows/edit?flow={f.name}")) \
                        .props("dense outline clickable")
                ui.button("Make a flow", icon="add_link", on_click=lambda: self._make_flow(trigger)) \
                    .props("flat dense no-caps size=sm").tooltip("A new flow that starts on this trigger")

    def _listening(self, trigger: CustomTrigger) -> list[Flow]:
        return [f for f in self._flows.all() if any(t.matches(CUSTOM, {"trigger": trigger.name}) for t in f.triggers)]

    async def _new(self) -> None:
        answer = await _ask_name("New custom trigger", "", "")
        if answer:
            try:
                self._store.add(*answer)
            except ValueError as e:
                ui.notify(str(e), type="warning")
            self.build.refresh()

    async def _rename(self, trigger: CustomTrigger) -> None:
        answer = await _ask_name("Rename / description", trigger.name, trigger.description)
        if not answer:
            return
        name, description = answer
        try:
            self._store.update(trigger.name, replace(trigger, name=name, description=description))
        except ValueError as e:
            ui.notify(str(e), type="warning")
            return
        if name != trigger.name:
            changed = self._flows.rename_custom_trigger(trigger.name, name)
            if changed:
                ui.notify(f"{len(changed)} flow(s) listen to {name} now", type="positive")
        self.build.refresh()

    async def _delete(self, trigger: CustomTrigger) -> None:
        listening = self._listening(trigger)
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label(f"Delete the custom trigger {trigger.name}?").classes("font-semibold")
            if listening:
                ui.label(f"{len(listening)} flow(s) listen to it; they stay, but nothing starts them through it "
                         "any more.").classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete", icon="delete", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps color=negative")
        sure = await dialog
        dialog.delete()
        if sure:
            self._store.delete(trigger.name)
            self.build.refresh()

    async def _test(self, trigger: CustomTrigger) -> None:
        await self._fire.fire(trigger.name, platform="test", user="test")
        count = len(self._listening(trigger))
        ui.notify(f"Fired {trigger.name}: {count} flow(s) start", type="positive")

    def _remove(self, trigger: CustomTrigger, source: FlowTrigger) -> None:
        self._store.remove_source(trigger.name, source)
        self.build.refresh()

    async def _add_source(self, trigger: CustomTrigger) -> None:
        source = await SourceDialog(self._rewards).open()
        if source is not None:
            self._store.add_source(trigger.name, source)
            self.build.refresh()

    def _make_flow(self, trigger: CustomTrigger) -> None:
        name = self._flows.free_name(trigger.name)
        self._flows.save(Flow(name, trigger.name, triggers=(FlowTrigger(CUSTOM, {"trigger": trigger.name}),),
                              folder=FOLDER, description=f"Starts when the custom trigger {trigger.name} fires"))
        ui.navigate.to(f"/flows/edit?flow={name}")


def _source_text(source: FlowTrigger) -> str:
    """"Redeem: Lizard", "Chat message: !lizard"."""
    text = source_kinds().get(source.kind, source.kind)
    shown = [str(v) for k, v in source.match.items() if not k.endswith("_id") and k not in ROLE_KEYS]
    if roles_match(roles_of(source.match)):
        shown.append("only " + roles_text(roles_of(source.match)))
    return f"{text}: " + ", ".join(shown) if shown else text


async def _ask_name(title: str, name: str, description: str) -> tuple[str, str] | None:
    with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
        ui.label(title).classes("font-semibold")
        name_field = ui.input("Name", value=name).props("outlined dense autofocus").classes("w-full")
        text = ui.input("What it's for (optional)", value=description).props("outlined dense").classes("w-full")
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
            ui.button("OK", on_click=lambda: dialog.submit((name_field.value or "", text.value or ""))) \
                .props("unelevated no-caps")
    answer = await dialog
    dialog.delete()
    if not answer or not answer[0].strip():
        return None
    return answer[0].strip(), answer[1].strip()

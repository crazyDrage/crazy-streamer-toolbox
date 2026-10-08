from collections.abc import Awaitable, Callable

from nicegui import ui

from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.connections.left_out import left_out
from streamer_toolbox.core.triggers.custom_trigger import CUSTOM
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_KINDS

RewardChoices = Callable[[], Awaitable[dict[str, str]]]
# what can fire a custom trigger: the events a flow can start on, but not another custom trigger (no loops)


def source_kinds() -> dict[str, str]:
    """kind → its name, read each time: a plugin may have added a trigger since the toolbox started."""
    return {kind: text for kind, (_, text, _, _) in TRIGGER_KINDS.items()
            if kind not in (CUSTOM, "timer") and not left_out(kind)}


class SourceDialog:
    """One source for a custom trigger: what kind of event, and which one (a redeem picked from the list keeps the
    reward's id; others are typed like in a flow's triggers, * = any)."""

    def __init__(self, rewards: RewardChoices) -> None:
        self._rewards = rewards

    async def open(self) -> FlowTrigger | None:
        rewards: dict[str, str] = {}
        try:
            rewards = await self._rewards()
        except Exception:  # Twitch not connected: a redeem can still be typed by name
            pass
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label("Fired by").classes("text-lg font-semibold")
            kind = ui.select(source_kinds(), value="twitch.redeem", label="When").props("outlined dense") \
                .classes("w-full")

            @ui.refreshable
            def value_field() -> None:
                key, default = TRIGGER_KINDS[kind.value][2], TRIGGER_KINDS[kind.value][3]
                if kind.value == "twitch.redeem" and rewards:
                    state["field"] = ui.select(rewards, label="Reward", with_input=True) \
                        .props("outlined dense").classes("w-full")
                else:
                    state["field"] = ui.input(key.replace("_", " ").capitalize(), value=default) \
                        .props("outlined dense").classes("w-full")
                state["key"] = key

            state: dict = {}
            kind.on_value_change(value_field.refresh)
            value_field()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        ok = await dialog
        dialog.delete()
        if not ok or not state["field"].value:
            return None
        value = str(state["field"].value)
        if kind.value == "twitch.redeem" and value in rewards:
            return FlowTrigger(kind.value, {"reward": rewards[value], "reward_id": value})
        return FlowTrigger(kind.value, {state["key"]: value})

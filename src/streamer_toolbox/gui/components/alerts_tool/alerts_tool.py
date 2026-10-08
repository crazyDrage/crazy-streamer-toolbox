from dataclasses import replace
from pathlib import Path

from nicegui import ui

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_router import AlertRouter
from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.gui.components.alerts_tool.alert_settings_dialog import AlertSettingsDialog


class AlertsTool:
    """The Alerts part of the Overlay page: one short block per kind of event (Follow, Sub, Resub, Gift subs,
    Cheer, Raid, Tip): on / off, what it says and shows in one line, Test, and Settings (the window with
    everything: AlertSettingsDialog)."""

    def __init__(self, store: AlertStore, router: AlertRouter, queue: AlertQueue) -> None:
        self._store = store
        self._router = router
        self._queue = queue

    def build(self) -> None:
        with ui.element("div").classes("grid gap-3 w-full md:grid-cols-2 xl:grid-cols-3 items-start"):
            for rule in self._store.all():
                self._rule(rule.event)

    def _rule(self, event: str) -> None:
        rule = self._store.get(event)
        with ui.card().classes("w-full gap-1"):
            with ui.row().classes("items-center no-wrap w-full gap-2"):
                ui.switch(value=rule.on, on_change=lambda e: self._store.save(
                    replace(self._store.get(event), on=e.value))).props("dense")
                ui.label(rule.title).classes("text-lg font-semibold flex-1")
                ui.button("Test", icon="play_arrow", on_click=lambda: self._test(event)) \
                    .props("no-caps outline dense").tooltip("Shows this alert now with a test name")
                ui.button("Settings", icon="tune", on_click=lambda: AlertSettingsDialog(
                    self._store, self._queue, event, self._summary.refresh).open()) \
                    .props("no-caps unelevated dense").tooltip("Text, picture, sound, where the words sit, "
                                                               "animations: with a preview")
            self._summary(event)

    @ui.refreshable_method
    def _summary(self, event: str) -> None:
        """What the alert says and shows, in two small lines."""
        rule = self._store.get(event)
        ui.label(rule.text or "(no text)").classes("text-sm break-all")
        ui.label(summary(rule)).classes("text-xs opacity-60 break-all")

    async def _test(self, event: str) -> None:
        try:
            in_front = await self._router.test(event)
        except Exception as e:  # a picture or sound that isn't there
            ui.notify(str(e), type="negative", multi_line=True)
            return
        where = "showing now" if not in_front else f"{in_front} in front of it"
        note = "" if self._queue.overlays else " (in the preview only: OBS isn't showing the overlay)"
        ui.notify(f"{AlertRule.default(event).title} test alert: {where}{note}", type="positive")


def summary(rule: AlertRule) -> str:
    """"party.gif · ding.ogg · 5 s · on the picture: name, amount" / "no picture · no sound · 5 s"."""
    on_picture = [part.title.casefold() for part in rule.parts if part.on_picture]
    bits = [Path(rule.image).name if rule.image else "no picture", Path(rule.sound).name if rule.sound else "no sound",
            f"{rule.seconds:g} s"]
    if on_picture:
        bits.append("on the picture: " + ", ".join(on_picture))
    if rule.variations:
        bits.append(f"{len(rule.variations)} bigger alert{'s' if len(rule.variations) > 1 else ''}")
    return " · ".join(bits)

from dataclasses import replace

from nicegui import ui

from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward

NUMBER = "outlined dense"


class RewardDialog:
    """Creates or changes a channel point reward: title, cost, the text viewers see, whether they type something,
    colour, limits (0 = none) and the queue. open() gives the reward to save, or None (cancelled)."""

    def __init__(self, reward: TwitchReward | None) -> None:
        self._reward = reward or TwitchReward("", paused=True)
        self._new = reward is None

    async def open(self) -> TwitchReward | None:
        r = self._reward
        with ui.dialog() as dialog, ui.card().classes("w-[520px] max-w-[96vw] gap-3"):
            ui.label("New reward" if self._new else f"Reward: {r.title}").classes("text-lg font-semibold")
            title = ui.input("Title (what viewers see)", value=r.title).props(NUMBER).classes("w-full")
            with ui.row().classes("w-full no-wrap gap-3"):
                cost = ui.number("Cost (points)", value=r.cost, min=1, precision=0).props(NUMBER).classes("flex-1")
                color = ui.color_input("Colour", value=r.color).props("outlined dense").classes("flex-1")
            prompt = ui.textarea("Description (shown with it)", value=r.prompt).props(f"{NUMBER} autogrow") \
                .classes("w-full")
            needs_text = ui.switch("Viewers type a text (it arrives as input in the flow)", value=r.needs_text)
            ui.label("Limits (0 = no limit)").classes("text-sm font-semibold")
            with ui.row().classes("w-full no-wrap gap-3"):
                cooldown = ui.number("Cooldown (s)", value=r.cooldown, min=0, precision=0).props(NUMBER) \
                    .classes("flex-1")
                per_stream = ui.number("Max per stream", value=r.max_per_stream, min=0, precision=0) \
                    .props(NUMBER).classes("flex-1")
                per_user = ui.number("Max per viewer", value=r.max_per_user, min=0, precision=0).props(NUMBER) \
                    .classes("flex-1")
            skip_queue = ui.switch("Skip the request queue", value=r.skip_queue)
            ui.label("On: redeems count as done at once, so they can't be refunded any more (also not by "
                     "\"Refund the redeem if it fails\").").classes("text-xs opacity-60 -mt-2")
            with ui.row().classes("gap-4"):
                enabled = ui.switch("On (viewers see it)", value=r.enabled)
                paused = ui.switch("Paused", value=r.paused)
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Create" if self._new else "Save", icon="check",
                          on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        ok = await dialog
        result = None
        if ok and (title.value or "").strip():
            result = replace(r, title=title.value.strip(), cost=int(cost.value or 1), color=color.value or r.color,
                             prompt=prompt.value or "", needs_text=bool(needs_text.value),
                             cooldown=int(cooldown.value or 0), max_per_stream=int(per_stream.value or 0),
                             max_per_user=int(per_user.value or 0), skip_queue=bool(skip_queue.value),
                             enabled=bool(enabled.value), paused=bool(paused.value))
        elif ok:
            ui.notify("A reward needs a title", type="warning")
        dialog.delete()
        return result

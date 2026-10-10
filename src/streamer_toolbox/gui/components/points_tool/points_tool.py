from nicegui import ui

from streamer_toolbox.connections.mixitup.mixitup_point_bank import MixItUpPointBank
from streamer_toolbox.core.points.point_earner import PointEarner
from streamer_toolbox.core.points.point_rules import PointRules
from streamer_toolbox.core.points.point_store import PointStore

NUMBERS = (("per_time", "Points for chatting"), ("minutes", "…every (minutes)"), ("on_follow", "For a follow"),
           ("on_sub", "For a sub"), ("on_raid", "For a raid"), ("per_100_bits", "Per 100 bits"))


class PointsTool:
    """Points on the Tools page: the toolbox's own currency per viewer. Top: how viewers earn (PointRules) with
    one Save. Below: every viewer with points, a search, and a row's number to change by hand."""

    def __init__(self, store: PointStore, earner: PointEarner, mixitup: MixItUpPointBank | None = None) -> None:
        self._store = store
        self._earner = earner
        self._mixitup = mixitup

    def build(self) -> None:
        rules = self._earner.rules
        with ui.card().classes("w-full gap-2"):
            ui.label("How viewers earn").classes("text-lg font-semibold")
            ui.label("Viewers get points every few minutes: those who write in chat, and on Twitch also those "
                     "who only watch (lurkers). Follows, subs, raids and cheers give a bonus. Flows use the "
                     "Points boxes (Add, Spend, Get, Top).").classes("text-sm opacity-80")
            on = ui.switch("Give out points", value=rules.enabled)
            with ui.row().classes("gap-3 items-end w-full"):
                source = ui.select({"toolbox": "The points live in the toolbox",
                                    "mixitup": "Use Mix It Up's points"}, value=rules.source,
                                   label="Where the points live").props("dense").classes("w-72")
                currency = ui.input("Mix It Up's currency (empty = its first one)", value=rules.mixitup_currency) \
                    .props("dense").classes("w-64")
                currency.bind_visibility_from(source, "value", lambda value: value == "mixitup")
                if self._mixitup is not None:
                    ui.button("Move the amounts over from Mix It Up", icon="move_down",
                              on_click=lambda: self._move_over(currency.value or "", rows)).props("no-caps outline") \
                        .tooltip("Copies every viewer's amount of the Mix It Up currency into the toolbox's own "
                                 "points. Mix It Up's numbers stay as they are")
            ui.label("With Mix It Up's points, Mix It Up keeps giving them out by its own rules: the numbers "
                     "below (points for chatting, bonuses) are not used, and the Points boxes and the chat command "
                     "read and change Mix It Up's numbers.").classes("text-xs opacity-60") \
                .bind_visibility_from(source, "value", lambda value: value == "mixitup")
            with ui.row().classes("gap-3 items-end"):
                name = ui.input("What they are called", value=rules.name).props("dense").classes("w-40")
                numbers = {key: ui.number(label, value=getattr(rules, key), min=0, precision=0)
                           .props("dense").classes("w-36") for key, label in NUMBERS}
            only_live = ui.switch("Only while the stream is live", value=rules.only_live).props("dense")
            lurkers = ui.switch("Lurkers earn too (everyone in the Twitch chat, also who never writes)",
                                value=rules.lurkers).props("dense")
            never = ui.input("Never earn (bots; names separated by commas)", value=rules.never) \
                .props("dense").classes("w-full")
            streamer = ui.switch("I earn points too", value=rules.streamer_earns).props("dense")
            note = ui.label().classes("text-xs text-warning")
            note.bind_text_from(self._earner, "lurkers_note",
                                lambda text: f"Lurkers weren't paid last time: {text}" if text else "")
            with ui.row().classes("gap-3 items-end w-full"):
                command = ui.input("Chat command that tells a viewer their points (empty = none)",
                                   value=rules.command).props("dense").classes("w-72")
                answer = ui.input("The answer ({user}, {points}, {name})", value=rules.answer) \
                    .props("dense").classes("flex-1")

            def save() -> None:
                self._earner.set_rules(PointRules.from_dict({
                    "enabled": on.value, "name": name.value or "", "only_live": only_live.value,
                    "lurkers": lurkers.value, "source": source.value, "never": never.value or "",
                    "streamer_earns": streamer.value,
                    "mixitup_currency": (currency.value or "").strip(),
                    "command": (command.value or "").strip(), "answer": answer.value or "",
                    **{key: field.value or 0 for key, field in numbers.items()}}))
                ui.notify("Points settings saved", type="positive")

            ui.button("Save", icon="save", on_click=save).props("no-caps unelevated")
        with ui.card().classes("w-full gap-2"):
            with ui.row().classes("items-center w-full gap-3"):
                ui.label("Viewers").classes("text-lg font-semibold")
                search = ui.input(placeholder="search a name").props("dense clearable").classes("w-56")
                ui.space()
                ui.button("Add a viewer", icon="person_add", on_click=lambda: self._edit(rows, "", "twitch", 0)) \
                    .props("no-caps outline")

            @ui.refreshable
            def rows() -> None:
                wanted = (search.value or "").strip().casefold()
                viewers = [viewer for viewer in self._store.all() if wanted in viewer["user"].casefold()]
                if not viewers:
                    ui.label("Nobody has points yet." if not wanted else "No viewer with that name.") \
                        .classes("opacity-70")
                for viewer in viewers[:200]:
                    with ui.row().classes("items-center no-wrap w-full gap-3"):
                        ui.label(viewer["user"]).classes("flex-1 font-medium")
                        ui.label(viewer["platform"]).classes("w-24 text-xs opacity-60")
                        ui.label(str(viewer["points"])).classes("w-24 text-right font-mono")
                        ui.button(icon="edit", on_click=lambda v=viewer: self._edit(
                            rows, v["user"], v["platform"], v["points"])).props("flat round dense")
                if len(viewers) > 200:
                    ui.label(f"…and {len(viewers) - 200} more: search to find them.").classes("text-xs opacity-60")

            rows()
            search.on_value_change(rows.refresh)
            ui.timer(10.0, rows.refresh)  # payouts change the numbers without a click here

    async def _move_over(self, currency: str, rows: ui.refreshable) -> None:
        """Mix It Up's amounts into the toolbox's own points, after he said yes."""
        rules = self._earner.rules
        try:
            self._earner.rules = PointRules.from_dict({**rules.to_dict(), "mixitup_currency": currency.strip()})
            viewers = await self._mixitup.viewers()
        except Exception as e:
            ui.notify(f"Mix It Up's points could not be read: {str(e).strip(chr(39) + chr(34))}", type="negative",
                      multi_line=True)
            return
        finally:
            self._earner.rules = rules
        if not viewers:
            ui.notify("Nobody has any of that currency in Mix It Up.", type="info")
            return
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] gap-3"):
            ui.label(f"Move {len(viewers)} viewers' amounts over?").classes("text-lg font-semibold")
            ui.label(f"Each of them gets the amount they have in Mix It Up ({sum(v['points'] for v in viewers)} in "
                     "all) as their points in the toolbox. A viewer who already has points here: the Mix It Up "
                     "amount replaces them. Mix It Up itself isn't changed.").classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Move over", on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        sure = await dialog
        dialog.delete()
        if not sure:
            return
        for viewer in viewers:
            self._store.set(viewer["user"], viewer["points"], viewer["platform"])
        rows.refresh()
        ui.notify(f"{len(viewers)} viewers' amounts are in the toolbox now", type="positive")

    async def _edit(self, rows: ui.refreshable, user: str, platform: str, points: int) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label(f"Points of {user}" if user else "Add a viewer").classes("text-lg font-semibold")
            name = ui.input("Name", value=user).props("dense" + (" readonly" if user else "")).classes("w-full")
            where = ui.select(["twitch", "youtube", "rumble"], value=platform, label="Platform") \
                .props("dense" + (" readonly" if user else "")).classes("w-full")
            amount = ui.number("Points", value=points, min=0, precision=0).props("dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                if user:
                    ui.button("Remove", on_click=lambda: dialog.submit("remove")).props("flat no-caps color=negative")
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Save", on_click=lambda: dialog.submit("save")).props("unelevated no-caps")
        chosen = await dialog
        dialog.delete()
        who = (name.value or "").strip()
        if chosen == "remove":
            self._store.remove(user, platform)
        elif chosen == "save" and who:
            self._store.set(who, int(amount.value or 0), where.value)
        rows.refresh()

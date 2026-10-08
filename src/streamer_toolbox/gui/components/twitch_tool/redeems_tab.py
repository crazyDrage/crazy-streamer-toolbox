from dataclasses import replace

from nicegui import app, ui

from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.interfaces.reward_manager import RewardManager
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore
from streamer_toolbox.gui.components.folder_field import FolderField
from streamer_toolbox.gui.components.twitch_tool.reward_dialog import RewardDialog

REDEEM = "twitch.redeem"
FOLDER = "Redeems"  # where Make a flow puts new flows
SORTS = {"name": "Name A-Z", "cost": "Cost: low first", "cost_high": "Cost: high first",
         "connected": "Connected first", "state": "On first, paused / off last"}


class RedeemsTab:
    """The Twitch tool's Redeems tab: every channel point reward with its state and the flows it starts.
    Rewards the toolbox made can be edited, paused, switched off and deleted here, and only their redeems can be
    refunded (Twitch's rule); dashboard rewards can only start flows. Make a flow: a new flow with a redeem trigger
    on this reward (kept by its ID, so renaming the reward on Twitch doesn't break it).

    Connect: straight to a flow (a new one, or added to one that exists) or through a custom trigger (the reward
    becomes one of its sources; every flow listening to the trigger starts). Sort and search on top."""

    def __init__(self, rewards: RewardManager, flows: FlowLibrary, triggers: CustomTriggerStore) -> None:
        self._rewards = rewards
        self._flows = flows
        self._triggers = triggers
        self._list: list[TwitchReward] | None = None
        self._error = ""
        self._search = ""

    def build(self) -> None:
        with ui.row().classes("items-center w-full gap-2"):
            ui.button("New reward", icon="add", on_click=lambda: self._edit(None)).props("unelevated no-caps")
            ui.button(icon="refresh", on_click=self._load).props("flat round").tooltip("Read Twitch again")
            search = ui.input(placeholder="Search rewards").props("dense outlined clearable").classes("w-48")
            search.on_value_change(lambda e: self._find(e.value))
            ui.select(SORTS, value=app.storage.general.get("redeems_sort", "name"), label="Sort",
                      on_change=lambda e: self._sort(e.value)).props("dense outlined options-dense").classes("w-56")
        ui.label("Only rewards the toolbox made can be changed here and refunded; rewards made on Twitch's "
                 "dashboard can still start flows.").classes("text-xs opacity-60")
        self._rows()
        ui.timer(0.05, self._load, once=True)

    async def _load(self) -> None:
        try:
            self._list, self._error = await self._rewards.list_rewards(), ""
        except Exception as e:  # not connected, ...
            self._list, self._error = [], f"Can't read the rewards: {e}"
        self._rows.refresh()

    @ui.refreshable_method
    def _rows(self) -> None:
        if self._error:
            ui.label(self._error + " (Connections → Twitch)").classes("text-warning")
            return
        if self._list is None:
            ui.label("Reading Twitch...").classes("opacity-70")
            return
        if not self._list:
            ui.label("No channel point rewards yet: New reward makes one.").classes("opacity-70")
            return
        shown = self._sorted([r for r in self._list if self._search.casefold() in r.title.casefold()])
        if not shown:
            ui.label(f"No reward matches {self._search!r}.").classes("opacity-70")
            return
        mine = [r for r in shown if r.by_toolbox]
        others = [r for r in shown if not r.by_toolbox]
        for title, rewards in (("Made by the toolbox", mine), ("Made on Twitch's dashboard", others)):
            if rewards:
                ui.label(f"{title} ({len(rewards)})").classes("text-sm font-semibold pt-3")
                with ui.column().classes("w-full gap-1"):
                    for reward in rewards:
                        self._row(reward)

    def _row(self, reward: TwitchReward) -> None:
        # wraps on a phone: the buttons go to their own line under the reward
        with ui.row().classes("items-center w-full gap-x-3 gap-y-1 px-2 py-2 rounded hover:bg-primary/10"):
            with ui.element("div").classes("w-10 h-10 rounded shrink-0 flex items-center justify-center") \
                    .style(f"background:{reward.color}"):
                if reward.image:
                    ui.image(reward.image).classes("w-8 h-8")
            with ui.column().classes("gap-0 min-w-[12rem] flex-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(reward.title).classes("font-semibold")
                    if reward.paused:
                        ui.badge("paused", color="warning").props("text-color=black")
                    if not reward.enabled:
                        ui.badge("off", color="grey")
                ui.label(_details(reward)).classes("text-xs opacity-70")
                self._connections(reward)
            with ui.row().classes("items-center no-wrap gap-1 ml-auto"):
                with ui.button("Connect", icon="add_link").props("flat dense no-caps"):
                    with ui.menu():
                        ui.menu_item("Make a new flow for it", on_click=lambda: self._make_flow(reward))
                        ui.menu_item("Add it to a flow that exists", on_click=lambda: self._add_to_flow(reward))
                        ui.menu_item("Fire a custom trigger", on_click=lambda: self._to_trigger(reward))
                if reward.by_toolbox:
                    ui.switch("paused", value=reward.paused,
                              on_change=lambda e: self._save(replace(reward, paused=e.value))).props("dense")
                    ui.switch("on", value=reward.enabled,
                              on_change=lambda e: self._save(replace(reward, enabled=e.value))).props("dense")
                    ui.button(icon="edit", on_click=lambda: self._edit(reward)).props("flat round dense") \
                        .tooltip("Edit")
                    ui.button(icon="delete", on_click=lambda: self._delete(reward)) \
                        .props("flat round dense color=negative").tooltip("Delete on Twitch")

    def _event(self, reward: TwitchReward) -> dict[str, str]:
        return {"reward": reward.title, "reward_id": reward.id}

    def _flows_of(self, reward: TwitchReward) -> list[Flow]:
        return [f for f in self._flows.all() if any(t.matches(REDEEM, self._event(reward)) for t in f.triggers)]

    def _triggers_of(self, reward: TwitchReward) -> list[str]:
        return [t.name for t in self._triggers.all() if t.fired_by(REDEEM, self._event(reward))]

    def _connections(self, reward: TwitchReward) -> None:
        """What a redeem of it starts: flows (straight) and custom triggers (and through them, their flows)."""
        flows, triggers = self._flows_of(reward), self._triggers_of(reward)
        if flows or triggers:
            with ui.row().classes("gap-1 pt-1"):
                for flow in flows:
                    ui.chip(flow.label, icon="account_tree",
                            on_click=lambda f=flow: ui.navigate.to(f"/flows/edit?flow={f.name}")) \
                        .props("dense outline clickable").tooltip("Starts this flow: open it")
                for name in triggers:
                    ui.chip(name, icon="sensors", on_click=lambda: ui.navigate.to("/triggers")) \
                        .props("dense outline clickable color=warning") \
                        .tooltip("Fires this custom trigger: see it on the Triggers page")

    def _find(self, words: str | None) -> None:
        self._search = (words or "").strip()
        self._rows.refresh()

    def _sort(self, how: str) -> None:
        app.storage.general["redeems_sort"] = how
        self._rows.refresh()

    def _sorted(self, rewards: list[TwitchReward]) -> list[TwitchReward]:
        how = app.storage.general.get("redeems_sort", "name")
        by_name = sorted(rewards, key=lambda r: r.title.casefold())
        if how == "cost":
            return sorted(by_name, key=lambda r: r.cost)
        if how == "cost_high":
            return sorted(by_name, key=lambda r: -r.cost)
        if how == "connected":
            return sorted(by_name, key=lambda r: not (self._flows_of(r) or self._triggers_of(r)))
        if how == "state":
            return sorted(by_name, key=lambda r: (not r.enabled, r.paused))
        return by_name

    async def _add_to_flow(self, reward: TwitchReward) -> None:
        flows = {f.name: f.label for f in self._flows.all()}
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label(f"Start a flow when someone redeems {reward.title}").classes("font-semibold")
            pick = ui.select(flows, label="Flow", with_input=True).props("outlined dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", on_click=lambda: dialog.submit(pick.value)).props("unelevated no-caps")
        name = await dialog
        dialog.delete()
        flow = self._flows.get(name) if name else None
        if flow is None:
            return
        trigger = FlowTrigger(REDEEM, self._event(reward))
        if trigger not in flow.triggers:
            self._flows.save(replace(flow, triggers=(*flow.triggers, trigger)))
        ui.notify(f"{flow.label} starts on {reward.title} now", type="positive")
        self._rows.refresh()

    async def _to_trigger(self, reward: TwitchReward) -> None:
        field = FolderField(self._triggers.names(), "", "Custom trigger (pick or type a new one)")
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label(f"Fire a custom trigger when someone redeems {reward.title}").classes("font-semibold")
            field.build().classes("w-full")
            ui.label("Every flow listening to that trigger starts (Triggers page). A new name makes a new trigger.") \
                .classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Connect", on_click=lambda: dialog.submit(field.value)).props("unelevated no-caps")
        name = await dialog
        dialog.delete()
        if not name:
            return
        self._triggers.add_source(name, FlowTrigger(REDEEM, self._event(reward)))
        ui.notify(f"{reward.title} fires the custom trigger {name}", type="positive")
        self._rows.refresh()

    async def _edit(self, reward: TwitchReward | None) -> None:
        changed = await RewardDialog(reward).open()
        if changed is not None:
            await self._save(changed)

    async def _save(self, reward: TwitchReward) -> None:
        try:
            await self._rewards.save_reward(reward)
        except Exception as e:
            ui.notify(f"Twitch said no: {e}", type="negative", multi_line=True)
        await self._load()

    async def _delete(self, reward: TwitchReward) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label(f"Delete the reward {reward.title} on Twitch?").classes("font-semibold")
            ui.label("Viewers can't redeem it any more; redeems still waiting get their points back. Flows that "
                     "start on it stay (their trigger then never fires).").classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete", icon="delete", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps color=negative")
        sure = await dialog
        dialog.delete()
        if not sure:
            return
        try:
            await self._rewards.delete_reward(reward.id)
        except Exception as e:
            ui.notify(f"Twitch said no: {e}", type="negative", multi_line=True)
        await self._load()

    def _make_flow(self, reward: TwitchReward) -> None:
        name = self._flows.free_name(reward.title)
        trigger = FlowTrigger(REDEEM, {"reward": reward.title, "reward_id": reward.id})
        self._flows.save(Flow(name, reward.title, triggers=(trigger,), folder=FOLDER,
                              description=f"Starts when someone redeems {reward.title}"))
        ui.notify("New flow in the folder Redeems. If SAMMI also reacts to this reward, it runs twice: take it out "
                  "in SAMMI when the flow is ready.", type="info", multi_line=True, timeout=8000)
        ui.navigate.to(f"/flows/edit?flow={name}")


def _details(reward: TwitchReward) -> str:
    """"300 points · viewers type a text · cooldown 60 s · 2 per viewer" in one line."""
    parts = [f"{reward.cost} points"]
    if reward.needs_text:
        parts.append("viewers type a text")
    if reward.cooldown:
        parts.append(f"cooldown {reward.cooldown} s")
    if reward.max_per_stream:
        parts.append(f"{reward.max_per_stream} per stream")
    if reward.max_per_user:
        parts.append(f"{reward.max_per_user} per viewer")
    if reward.skip_queue:
        parts.append("skips the queue (no refunds)")
    return " · ".join(parts)

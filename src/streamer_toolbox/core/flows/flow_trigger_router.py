import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_cooldowns import FlowCooldowns
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_skipped import FlowSkipped
from streamer_toolbox.core.flows.flow_stopped import FlowStopped
from streamer_toolbox.core.flows.flow_trigger import REWARDS
from streamer_toolbox.core.flows.flow_wire import START

log = logging.getLogger(__name__)
Report = Callable[[str, str, bool, Any], None]  # (who, action, ok, result or error), like ActivityLog.add
Refund = Callable[[dict[str, Any]], Awaitable[None]]  # gives a redeem's points back (TwitchConnection)
# these fire often: only failures go to the activity list, and a run still going is skipped
QUIET = {"timer", "vts.model_moved"}


class FlowTriggerRouter:
    """Listens on the EventBus and starts every flow with a matching trigger, at that trigger's Start box; the
    event's data is what its orange dots give (and ${event.key}: a redeem's reward, user, input, ...). When two
    of a flow's triggers fit one event, the first one starts it (one event, one run per flow)."""

    def __init__(self, library: FlowLibrary, runner: FlowRunner, report: Report | None = None,
                 refund: Refund | None = None, cooldowns: FlowCooldowns | None = None) -> None:
        self._library = library
        self._runner = runner
        self._report = report
        self._refund = refund
        self._cooldowns = cooldowns or FlowCooldowns()
        self._running: set[tuple[str, str]] = set()

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        self._keep_reward_names(kind, data)
        if kind == REWARDS:
            return
        # side by side, so a flow waiting in line doesn't hold back the others
        starts = [(flow, trigger) for flow in self._library.all()
                  if flow.enabled and flow.triggers_enabled  # a switched-off one stays quiet
                  for trigger in [next((t for t in flow.triggers if t.matches(kind, data)), None)] if trigger]
        await asyncio.gather(*(self._run(flow, kind, data, trigger.id) for flow, trigger in starts))

    async def _run(self, flow: Flow, kind: str, data: dict[str, Any], start: str) -> None:
        key = (flow.name, kind)
        if kind in QUIET and key in self._running:
            return
        wait = self._cooldowns.wait_left(flow, data)
        if wait > 0:
            self._held_back(flow, kind, f"on cooldown for {wait:.0f} more s")
            await self._give_back(flow, kind, data)
            return
        self._cooldowns.started(flow, data)
        self._running.add(key)
        try:
            result = await self._runner.run(flow, event=data, start=start or START)
        except FlowSkipped as e:  # it's set to skip while busy: not a failure
            self._held_back(flow, kind, str(e))
            await self._give_back(flow, kind, data)
            return
        except FlowStopped as e:  # stopped by hand: it ran, so the points aren't given back
            if self._report:
                self._report(kind, flow.action_name, False, e)
            return
        except Exception as e:
            log.warning("flow %s (from %s) failed: %s", flow.name, kind, e)
            if self._report:
                self._report(kind, flow.action_name, False, e)
            await self._give_back(flow, kind, data)
            return
        finally:
            self._running.discard(key)
        if self._report and kind not in QUIET:
            self._report(kind, flow.action_name, True, f"{len(result)} boxes")

    def _keep_reward_names(self, kind: str, data: dict[str, Any]) -> None:
        """Redeem triggers keep their reward's id; when Twitch shows a new title for it (a redeem, or the reward
        list when Twitch connects) the triggers take the new name."""
        if kind == "twitch.redeem":
            rewards = [{"id": data.get("reward_id", ""), "title": data.get("reward", "")}]
        elif kind == REWARDS:
            rewards = data.get("rewards", [])
        else:
            return
        for reward in rewards:
            if reward.get("id") and reward.get("title"):
                for name in self._library.rename_reward(reward["id"], reward["title"]):
                    log.info("flow %s: reward renamed on Twitch, trigger now says %r", name, reward["title"])

    def _held_back(self, flow: Flow, kind: str, why: str) -> None:
        if self._report and kind not in QUIET:
            self._report(kind, flow.action_name, True, why)

    async def _give_back(self, flow: Flow, kind: str, data: dict[str, Any]) -> None:
        """Refund on fail: a redeem's points go back (only works for rewards the toolbox made)."""
        if not (flow.refund_on_fail and kind == "twitch.redeem" and self._refund):
            return
        try:
            await self._refund(data)
        except Exception as e:
            log.warning("flow %s: refund failed: %s", flow.name, e)
            if self._report:
                self._report(kind, flow.action_name, False, f"points not given back: {e}")

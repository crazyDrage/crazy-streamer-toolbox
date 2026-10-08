"""Start the toolbox: python -m streamer_toolbox [--config config/toolbox.toml] [--port 8850] [--plugins <folder>]
[--open none|browser|window]

This process is the launcher: it opens the page and runs the toolbox itself as a child (--child), which it starts
again when the toolbox asks for a restart (Settings → Restart)."""
import argparse
import asyncio
import logging
import secrets
import sys
from pathlib import Path

from nicegui import Client, app, ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.api.action_router import build_action_router
from streamer_toolbox.api.caller_auth import CallerAuth
from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.events.common_events import CommonEvents
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.data.json_actions import JsonActions
from streamer_toolbox.core.data.list_actions import ListActions
from streamer_toolbox.core.data.object_actions import ObjectActions
from streamer_toolbox.core.data.split_actions import SplitActions
from streamer_toolbox.core.data.text_actions import TextActions
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.triggers.custom_trigger_actions import CustomTriggerActions
from streamer_toolbox.core.triggers.custom_trigger_router import CustomTriggerRouter
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.api.overlay_router import build_overlay_router
from streamer_toolbox.core.alerts.alert_actions import AlertActions
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_router import AlertRouter
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.gui.components.alerts_tool.alerts_tool import AlertsTool
from streamer_toolbox.gui.pages.overlay_page import OverlayPage
from streamer_toolbox.api.widget_router import build_widget_router
from streamer_toolbox.api.widget_sandbox_middleware import WidgetSandboxMiddleware
from streamer_toolbox.connections.streamelements_connection import StreamElementsConnection
from streamer_toolbox.connections.streamlabs_connection import StreamlabsConnection
from streamer_toolbox.connections.rumble_connection import RumbleConnection
from streamer_toolbox.connections.youtube_connection import YouTubeConnection
from streamer_toolbox.connections.streamsocket_connection import StreamSocketConnection
from streamer_toolbox.connections.crowdcontrol_connection import CrowdControlConnection
from streamer_toolbox.connections.discord_connection import DiscordConnection
from streamer_toolbox.connections.firebot_connection import FirebotConnection
from streamer_toolbox.connections.heartrate.heart_rate import EVENT as HEART_RATE, HeartRate
from streamer_toolbox.core.connections.left_out import LEFT_OUT, left_out
from streamer_toolbox.connections.hyperate_connection import HypeRateConnection
from streamer_toolbox.connections.lumia_connection import LumiaConnection
from streamer_toolbox.connections.pulsoid_connection import PulsoidConnection
from streamer_toolbox.connections.streamerbot_connection import StreamerbotConnection
from streamer_toolbox.connections.tiltify_connection import TiltifyConnection
from streamer_toolbox.connections.tits_connection import TitsConnection
from streamer_toolbox.connections.voicemod_connection import VoicemodConnection
from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.history.history_actions import HistoryActions
from streamer_toolbox.core.points.point_actions import PointActions
from streamer_toolbox.connections.mixitup.mixitup_point_bank import MixItUpPointBank
from streamer_toolbox.core.points.local_point_bank import LocalPointBank
from streamer_toolbox.core.points.point_earner import PointEarner
from streamer_toolbox.core.points.point_rules import PointRules
from streamer_toolbox.core.points.point_store import PointStore
from streamer_toolbox.gui.components.points_tool.points_tool import PointsTool
from streamer_toolbox.core.tips.tip_actions import TipActions
from streamer_toolbox.core.widgets.channel_lookup import ChannelLookup
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.latest_followers import LatestFollowers
from streamer_toolbox.core.widgets.missed_subscribers import MissedSubscribers
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback
from streamer_toolbox.core.widgets.widget_actions import WidgetActions
from streamer_toolbox.core.widgets.streamelements_elements import StreamElementsElements
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.streamelements_session import StreamElementsSession
from streamer_toolbox.core.widgets.subscriber_count import SubscriberCount
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.overlay_source import OverlaySource
from streamer_toolbox.gui.components.widgets_tool.widgets_tool import WidgetsTool
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.core.actions.wip_boxes import WIP_BOXES, shows_wip
from streamer_toolbox.core.testing.release_marker import is_release
from streamer_toolbox.core.testing.test_gate import TestGate
from streamer_toolbox.core.testing.test_inventory import TestInventory
from streamer_toolbox.core.testing.test_list import TestList
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_KINDS
from streamer_toolbox.gui.components.box_filter_panel import BoxFilterPanel
from streamer_toolbox.core.files.file_actions import FileActions
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.flows.timer_clock import TimerClock
from streamer_toolbox.core.popups.popup_actions import PopupActions
from streamer_toolbox.core.security.login_throttle import LoginThrottle
from streamer_toolbox.core.security.remote_access import RemoteAccess
from streamer_toolbox.core.security.signed_in_devices import SignedInDevices
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.variables.viewer_actions import ViewerActions
from streamer_toolbox.core.web.http_actions import HttpActions
from streamer_toolbox.core.system.program_actions import ProgramActions
from streamer_toolbox.core.system.time_actions import TimeActions
from streamer_toolbox.core.system.parent_watch import ParentWatch
from streamer_toolbox.core.system.toolbox_launcher import ToolboxLauncher
from streamer_toolbox.core.system.toolbox_restart import ToolboxRestart
from streamer_toolbox.gui.services.activity_log import ActivityLog
from streamer_toolbox.gui.components.app_shell import AREAS, AppShell
from streamer_toolbox.gui.components.flow_editor.trigger_catalog import group_of
from streamer_toolbox.gui.services.app_window_page_opener import AppWindowPageOpener
from streamer_toolbox.gui.services.browser_page_opener import BrowserPageOpener
from streamer_toolbox.gui.pages.connections_page import ConnectionsPage
from streamer_toolbox.gui.pages.flow_editor_page import FlowEditorPage
from streamer_toolbox.gui.pages.flows_page import FlowsPage
from streamer_toolbox.gui.pages.live_page import LivePage
from streamer_toolbox.gui.pages.login_page import LoginPage
from streamer_toolbox.gui.services.remote_login_middleware import RemoteLoginMiddleware
from streamer_toolbox.gui.services.nicegui_confirm_service import NiceGuiConfirmService
from streamer_toolbox.gui.services.nicegui_message_service import NiceGuiMessageService
from streamer_toolbox.gui.services.open_pages import OpenPages
from streamer_toolbox.gui.services.nicegui_plugin_context import NiceGuiPluginContext
from streamer_toolbox.gui.pages.plugins_page import PluginsPage
from streamer_toolbox.gui.pages.settings_page import SettingsPage
from streamer_toolbox.gui.components.twitch_tool.twitch_tool import TwitchTool
from streamer_toolbox.gui.pages.tools_page import ToolsPage, tool_slug
from streamer_toolbox.gui.pages.triggers_page import TriggersPage
from streamer_toolbox.gui.pages.variables_page import VariablesPage
from streamer_toolbox.gui.services.ui_registry import UiRegistry
from streamer_toolbox.core.media.miniaudio_sound_player import MiniaudioSoundPlayer
from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe
from streamer_toolbox.core.media.sound_actions import SoundActions
from streamer_toolbox.core.media.video_actions import VideoActions
from streamer_toolbox.connections.keyboard.pynput_key_listener import PynputKeyListener
from streamer_toolbox.connections.keyboard_connection import KEY_PRESSED, KeyboardConnection
from streamer_toolbox.connections.mixitup_connection import MixItUpConnection
from streamer_toolbox.connections.obs_connection import ObsConnection
from streamer_toolbox.plugins.plugin_loader import PluginLoader
from streamer_toolbox.plugins.plugin_switches import PluginSwitches
from streamer_toolbox.connections.sammi_connection import SammiConnection
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.veadotube_connection import VeadotubeConnection
from streamer_toolbox.connections.vnyan_connection import VNyanConnection
from streamer_toolbox.connections.warudo_connection import WarudoConnection
from streamer_toolbox.connections.twitch_connection import TwitchConnection
from streamer_toolbox.connections.vts_connection import VtsConnection
from streamer_toolbox.connections.vtube_studio.vts_position_store import VtsPositionStore
from streamer_toolbox.connections.sammi.toolbox_deck import toolbox_deck

REPO_ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("streamer_toolbox")


BOX_CATEGORY = {"vtube_studio": "vts"}  # connection id → its boxes' category, where they differ


def assemble(args: argparse.Namespace, config: ToolboxConfig) -> tuple[TestGate, ToolboxRestart]:
    """Puts the whole toolbox together (connections, boxes, flows, pages) without starting it: nothing
    connects and no port is opened before ui.run. main() runs it; devtools/tested only reads what is in it."""
    actions = ActionRegistry()
    parked = set() if shows_wip(config.tables) else set(WIP_BOXES)
    actions.park(parked)
    gate = TestGate(TestList(), is_release(), parked)  # a build only offers what the test record says is tested
    ui_registry = UiRegistry()
    pages = OpenPages()
    confirm = NiceGuiConfirmService(pages)
    activity = ActivityLog()
    shell = AppShell(ui_registry, pages)
    events = EventBus()
    loader = PluginLoader(args.plugins, lambda plugin_id, folder: NiceGuiPluginContext(
        plugin_id, actions, ui_registry, confirm, shell.frame, folder, args.config.parent, events))
    loader.load_all(config.plugins_enabled)
    ui_registry.category_titles.update({pid: m.name for pid, m in loader.manifests.items()})

    port = args.port or config.port
    events.subscribe(CommonEvents(events).handle)
    twitch_tokens = OAuthTokenStore(args.config.parent / "twitch_token.json")
    twitch = TwitchConnection(config.tables.get("twitch", {}), twitch_tokens, events)
    probe = Mp4HeaderProbe()

    def wants_key(name: str) -> bool:
        """Only keys a flow's Key trigger names become events (flows is set further down, before any key)."""
        return any(trigger.matches(KEY_PRESSED, {"key": name}) for flow in flows.all() for trigger in flow.triggers)

    mixitup = MixItUpConnection(config.tables.get("mixitup", {}))
    heart = HeartRate(events)
    if not left_out(HEART_RATE):
        heart.add_to(actions)
    connections = ConnectionManager([connection for connection in [
        ObsConnection(config.obs, probe),
        SammiConnection(config.tables.get("sammi", {}), lambda: toolbox_deck(actions, config.callers, port)),
        mixitup,
        VtsConnection(config.tables.get("vtube_studio", {}), args.config.parent / "vts_token.txt",
                      VtsPositionStore(args.config.parent / "vts_positions.toml"), events=events),
        twitch,
        KeyboardConnection(config.tables.get("keyboard", {}), PynputKeyListener(), events, wants_key),
        StreamElementsConnection(config.tables.get("streamelements", {}),
                                 args.config.parent / "streamelements_token.txt", events),
        StreamlabsConnection(config.tables.get("streamlabs", {}), args.config.parent / "streamlabs_token.txt",
                             events),
        RumbleConnection(config.tables.get("rumble", {}), args.config.parent / "rumble_address.txt", events),
        YouTubeConnection(config.tables.get("youtube", {}),
                          OAuthTokenStore(args.config.parent / "youtube_token.json"), events),
        StreamSocketConnection(config.tables.get("streamsocket", {}), args.config.parent / "streamsocket_secret.txt",
                               events, lambda: (twitch_tokens.load().user_id if twitch_tokens.load() else "")),
        VNyanConnection(config.tables.get("vnyan", {})),
        WarudoConnection(config.tables.get("warudo", {})),
        VeadotubeConnection(config.tables.get("veadotube", {}), events),
        TitsConnection(config.tables.get("tits", {}), events),
        StreamerbotConnection(config.tables.get("streamerbot", {}),
                              args.config.parent / "streamerbot_password.txt", events),
        FirebotConnection(config.tables.get("firebot", {})),
        LumiaConnection(config.tables.get("lumia", {}), args.config.parent / "lumia_token.txt", events),
        VoicemodConnection(config.tables.get("voicemod", {}), args.config.parent / "voicemod_key.txt"),
        PulsoidConnection(config.tables.get("pulsoid", {}), args.config.parent / "pulsoid_token.txt", heart),
        HypeRateConnection(config.tables.get("hyperate", {}), args.config.parent / "hyperate_key.txt", heart),
        DiscordConnection(config.tables.get("discord", {}), args.config.parent / "discord_webhook.txt"),
        TiltifyConnection(config.tables.get("tiltify", {}), args.config.parent / "tiltify_secret.txt", events),
        CrowdControlConnection(config.tables.get("crowdcontrol", {}), events),
        *ui_registry.connections,  # a plugin's own (ctx.add_connection)
    ] if connection.id not in LEFT_OUT and gate.keeps(connection.id)], ConfigTableWriter(args.config))
    for connection in ui_registry.connections:
        connection.configure(config.tables.get(connection.id, {}))
    for connection in connections.all():
        connection.add_actions(actions)
    variables = VariableStore(args.config.parent / "variables.json")
    LogicActions(variables).add_to(actions)
    custom_triggers = CustomTriggerStore(args.config.parent / "custom_triggers.json")

    plugin_switches = PluginSwitches(args.config.parent / "plugins_off.json")

    def switched_off() -> dict[str, str]:
        """Box category → program, for the connections and plugins that are off: their boxes stay out of the
        Add box window and their triggers out of Add trigger."""
        off = {BOX_CATEGORY.get(c.id, c.id): c.title for c in connections.all() if not c.settings["enabled"]}
        plugins_off = {pid: f"{loader.manifests[pid].name if pid in loader.manifests else pid} (plugin)"
                       for pid in plugin_switches.off() if pid in loader.loaded}
        return off | plugins_off

    box_filters = BoxFilterStore(args.config.parent / "box_filters.json")
    fire_trigger = CustomTriggerActions(custom_triggers, events)
    fire_trigger.add_to(actions)
    FileActions().add_to(actions)
    ListActions(variables).add_to(actions)
    JsonActions().add_to(actions)
    SplitActions().add_to(actions)
    ObjectActions().add_to(actions)
    TextActions().add_to(actions)
    HttpActions().add_to(actions)
    ProgramActions().add_to(actions)
    ViewerActions(variables).add_to(actions)
    TimeActions().add_to(actions)
    PopupActions(NiceGuiMessageService(pages), confirm).add_to(actions)
    sound_folder = config.tables.get("sound", {}).get("folder")
    VideoActions(probe).add_to(actions)
    SoundActions(MiniaudioSoundPlayer(), Path(sound_folder) if sound_folder else None).add_to(actions)
    runner = FlowRunner(actions, variables)
    flows = FlowLibrary(FlowStore(args.config.parent / "flows"), FlowStore(args.config.parent / "flow_templates"),
                        runner, actions)
    flows.load()
    async def refund(data: dict) -> None:
        await twitch.finish_redeem(data.get("reward_id", ""), data.get("redemption_id", ""), refund=True)

    events.subscribe(FlowTriggerRouter(flows, runner, activity.add, refund).handle)
    events.subscribe(CustomTriggerRouter(custom_triggers, events).handle)
    alert_queue = AlertQueue()
    AlertActions(alert_queue).add_to(actions)
    alert_store = AlertStore(args.config.parent / "alerts.json")
    alert_router = AlertRouter(alert_store, alert_queue)
    events.subscribe(alert_router.handle)
    widget_store = WidgetStore(args.config.parent / "widgets")

    def channel_info() -> dict[str, str]:
        """The streamer's Twitch login name and id, for widgets (their code checks "is this the streamer?")."""
        token = twitch_tokens.load()
        twitch_side = {"username": token.login, "providerId": token.user_id} if token else {}
        return {**twitch_side, "id": streamelements_import.account_id()}

    streamelements_import = StreamElementsImport(args.config.parent / "streamelements_token.txt")
    history = EventHistory(args.config.parent / "history" / "events.jsonl")
    HistoryActions(history).add_to(actions)
    widget_hub = WidgetHub(WidgetSession(args.config.parent / "cache" / "widget_session.json", history),
                           channel_info)
    widget_fallback = StreamElementsFallback(config.tables.get("widgets", {}), ConfigTableWriter(args.config))
    events.subscribe(widget_hub.handle)
    missed_subs = MissedSubscribers(twitch.helix, channel_info, widget_hub.session, history,
                                    args.config.parent / "history" / "subscribers.json")
    events.subscribe(missed_subs.handle)
    WidgetActions(widget_hub, widget_store).add_to(actions)
    TipActions(events).add_to(actions)
    points = PointStore(args.config.parent / "points" / "points.json")
    own_points = LocalPointBank(points)
    mixitup_points = MixItUpPointBank(mixitup.send, lambda: earner.rules.mixitup_currency)

    def point_bank() -> LocalPointBank | MixItUpPointBank:
        """Where the points live right now (the Points page's choice)."""
        return mixitup_points if earner.rules.source == "mixitup" else own_points

    PointActions(point_bank).add_to(actions)

    async def say(platform: str, text: str) -> None:
        """The points command's answer, in the chat it was asked in (Rumble can't be written to)."""
        await actions.run(f"{platform}.send_chat", message=text)

    earner = PointEarner(points, PointRules.from_dict(config.tables.get("points", {})),
                         ConfigTableWriter(args.config), say, viewers=twitch.viewers, live=twitch.is_live,
                         bank=point_bank,
                         own=lambda: (twitch_tokens.load().login if twitch_tokens.load() else ""))
    events.subscribe(earner.handle)

    async def custom_trigger_names() -> list[str]:
        return custom_triggers.names()
    clock = TimerClock(flows, events)
    app.on_startup(connections.start_all)
    app.on_startup(clock.start)
    payouts: list[asyncio.Task] = []  # keeps the task alive

    async def start_payouts() -> None:
        payouts.append(asyncio.get_running_loop().create_task(earner.run()))
        payouts.append(asyncio.get_running_loop().create_task(look_for_missed_subs()))

    async def look_for_missed_subs() -> None:
        await asyncio.sleep(20)  # once Twitch is connected
        found = await missed_subs.check()
        if found:
            log.info("%d sub(s) came in while the toolbox was off", len(found))

    app.on_startup(start_payouts)
    app.on_shutdown(connections.stop_all)
    app.on_shutdown(clock.stop)

    app.add_static_files("/static", Path(__file__).parent / "gui" / "static")
    access = RemoteAccess(config.tables.get("api", {}), config.tables.get("access", {}),
                          ConfigTableWriter(args.config))
    devices = SignedInDevices(args.config.parent / "signed_in_devices.json")
    app.add_middleware(WidgetSandboxMiddleware)
    app.add_middleware(RemoteLoginMiddleware, access=access, devices=devices, is_login_client=_is_login_client)
    ui.page("/login", title="Sign in · streamer-toolbox")(LoginPage(access, LoginThrottle(), devices).build)
    app.include_router(build_action_router(actions, CallerAuth(list(config.callers)), activity.add))
    app.include_router(build_overlay_router(alert_queue))
    app.include_router(build_widget_router(widget_store, widget_hub, WidgetPage(widget_hub.session, channel_info),
                                           ChannelLookup(twitch.helix, channel_info), widget_fallback,
                                           EmoteLookup(), LatestFollowers(twitch.helix, channel_info),
                                           SubscriberCount(twitch.helix, channel_info)))
    shell.page("Live", "/", LivePage(actions, ui_registry, activity,
                                     DeckStore(args.config.parent / "live_deck.json", flows.all), flows).build)
    shell.page("Flows", "/flows", FlowsPage(flows, actions, activity).build)
    shell.page("Edit flow", "/flows/edit", FlowEditorPage(flows, actions, runner, variables,
                                                            BoxValueFiles(args.config.parent / "box_values"),
                                                            {"twitch.redeem": twitch.reward_choices,
                                                             "custom": custom_trigger_names},
                                                            box_filters, switched_off).build)
    shell.page("Triggers", "/triggers", TriggersPage(custom_triggers, flows, fire_trigger,
                                                     twitch.reward_choices).build)
    shell.page("Variables", "/variables", VariablesPage(variables, flows).build)
    ui_registry.tools.insert(0, ("toolbox", "Twitch", "live_tv", "Your channel point rewards (and more Twitch things "
                                 "later)", lambda: TwitchTool(twitch, flows, custom_triggers).build()))
    ui_registry.tools.insert(1, ("toolbox", "Points", "toll", "Your own currency: how viewers earn it, and who has "
                                 "how much", lambda: PointsTool(points, earner, mixitup_points).build()))

    overlay_source = OverlaySource(actions)
    shell.page("Overlay", "/overlays", OverlayPage(
        AlertsTool(alert_store, alert_router, alert_queue),
        WidgetsTool(widget_store, widget_hub, overlay_source, port,
                    streamelements_import, widget_fallback, StreamElementsElements(streamelements_import),
                    StreamElementsSession(streamelements_import, history=history)),
        alert_queue, overlay_source, port).build)
    shell.page("Tools", "/tools", ToolsPage(ui_registry).build)
    shell.sub_items["/overlays"] = [("Alerts", "/overlays?show=alerts", "campaign"),
                                    ("Widgets", "/overlays?show=widgets", "widgets")]
    shell.sub_items["/tools"] = lambda: [(title, f"/tools?show={tool_slug(title)}", icon or "handyman")
                                         for _, title, icon, *_ in ui_registry.tools]
    shell.sub_items["/connections"] = [("Toolbox", "/connections?show=toolbox", "lan")] + [
        (c.title, f"/connections?show={c.id}", c.icon) for c in connections.all()]
    shell.page("Connections", "/connections", ConnectionsPage(config, args.config, ui_registry, connections).build)
    shell.page("Plugins", "/plugins", PluginsPage(
        lambda: (loader.loaded, loader.failed, loader.disabled, loader.manifests), ui_registry,
        plugin_switches).build)
    restart = ToolboxRestart(app.shutdown, available=args.child)
    settings_page = SettingsPage(args.config, ui_registry, access, devices, port,
                                restart, BoxFilterPanel(box_filters, actions))
    shell.page("Settings", "/settings", settings_page.build)
    shell.sub_items["/settings"] = settings_page.sections

    def menu() -> list[tuple[str, str, list[tuple[str, str]]]]:
        """The side menu for the test record: every main tab with the pages below it. The tools and the
        connections are not pages here: they have rows of their own."""
        below = {"/flows": [("Edit flow", "/flows/edit")],
                 "/overlays": [(title, path) for title, path, _ in shell.sub_items["/overlays"]],
                 "/connections": [("Toolbox", "/connections?show=toolbox")],
                 "/plugins": [(title, path) for title, path, _ in ui_registry.pages],
                 "/settings": [(title, path) for title, path, _ in settings_page.sections()]}
        return [(title, path, below.get(path, [])) for title, path, _ in AREAS]

    gate.apply(actions, ui_registry.tools, lambda: TestInventory(
        actions, [(c.id, c.title) for c in connections.all()], [title for _, title, *_ in ui_registry.tools],
        {kind: (entry[1], group_of(kind)) for kind, entry in TRIGGER_KINDS.items()}, BOX_CATEGORY, menu()).items())
    shell.left_out = gate.untested_pages
    return gate, restart


def main() -> None:
    parser = argparse.ArgumentParser(prog="streamer_toolbox")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "toolbox.toml")
    parser.add_argument("--port", type=int, default=None, help="overrides [api] port")
    parser.add_argument("--plugins", type=Path, default=REPO_ROOT / "plugins")
    parser.add_argument("--open", choices=("none", "browser", "window"), default="none",
                        help="show the dashboard once running: browser tab or app window (Edge/Chrome)")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)  # run by the launcher
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = ToolboxConfig.read(args.config)
    if not args.child:
        sys.exit(_launch(args, config))
    log.info("config: %s", args.config if args.config.exists() else "none found, using defaults")
    _, restart = assemble(args, config)
    ParentWatch(sys.stdin.fileno(), app.shutdown).start()  # the launcher closes our stdin: window closed, Ctrl+C
    ui.run(host=config.host, port=args.port or config.port, title="streamer-toolbox", show=False, reload=False,
           storage_secret=_session_secret(args.config.parent / "session_secret.txt"))
    sys.exit(restart.exit_code)


def _launch(args: argparse.Namespace, config: ToolboxConfig) -> int:
    """The launcher: runs the toolbox as a child, opens the page once it answers, starts it again on Restart."""
    command = [sys.executable, "-m", "streamer_toolbox", "--child", "--config", str(args.config),
               "--plugins", str(args.plugins)] + (["--port", str(args.port)] if args.port else [])
    host = "127.0.0.1" if config.host in ("0.0.0.0", "::") else config.host  # 0.0.0.0 isn't an address to open
    launcher: ToolboxLauncher | None = None
    opener = None
    if args.open != "none":
        opener = BrowserPageOpener()
        if args.open == "window":
            # closing the window stops the toolbox (his wish, round 12); a restart keeps the window
            opener = AppWindowPageOpener(opener, profile_dir=args.config.parent / "app_window",
                                         on_closed=lambda: launcher.stop())
    launcher = ToolboxLauncher(command, f"http://{host}:{args.port or config.port}", opener)
    return launcher.run()


def _is_login_client(client_id: str) -> bool:
    """Whether that open page is the login page: a device that isn't signed in may only use the socket for it."""
    client = Client.instances.get(client_id)
    return client is not None and client.page.path == "/login"


def _session_secret(path: Path) -> str:
    """Signs the cookie that keeps another device signed in; made once, kept in config/ (not in git)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


if __name__ in {"__main__", "__mp_main__"}:
    main()

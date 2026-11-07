import argparse
import asyncio
import logging
from pathlib import Path

from nicegui import Client, app, ui

from streamer_toolbox.api.action_router import build_action_router
from streamer_toolbox.api.caller_auth import CallerAuth
from streamer_toolbox.api.overlay_router import build_overlay_router
from streamer_toolbox.api.widget_router import build_widget_router
from streamer_toolbox.api.widget_sandbox_middleware import WidgetSandboxMiddleware
from streamer_toolbox.assembly.built_in_connections import BuiltInConnections
from streamer_toolbox.assembly.own_boxes import OwnBoxes
from streamer_toolbox.connections.heartrate.heart_rate import EVENT as HEART_RATE, HeartRate
from streamer_toolbox.connections.keyboard_connection import KEY_PRESSED
from streamer_toolbox.connections.mixitup.mixitup_point_bank import MixItUpPointBank
from streamer_toolbox.connections.mixitup_connection import MixItUpConnection
from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.sammi.toolbox_deck import toolbox_deck
from streamer_toolbox.connections.twitch_connection import TwitchConnection
from streamer_toolbox.core.actions.action_registry import PLUGINS, SERVICES, ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.core.actions.wip_boxes import WIP_BOXES, shows_wip
from streamer_toolbox.core.alerts.alert_actions import AlertActions
from streamer_toolbox.core.alerts.alert_backup import AlertBackup
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_actions import EventActions
from streamer_toolbox.core.event_types.event_conversion import EventConversion
from streamer_toolbox.core.event_types.events_upgrade import EventsUpgrade
from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_sender import EventSender
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.connections.left_out import LEFT_OUT, left_out
from streamer_toolbox.core.connections.secrets_folder import SecretsFolder
from streamer_toolbox.core.deck.deck_images import URL as DECK_IMAGES_URL
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.events.chat_memory import ChatMemory
from streamer_toolbox.core.events.common_events import CommonEvents
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_recording import EventRecording
from streamer_toolbox.core.events.last_events import LastEvents
from streamer_toolbox.connections.twitch.twitch_role_list import TwitchRoleList
from streamer_toolbox.core.events.role_book import RoleBook
from streamer_toolbox.core.events.role_loader import RoleLoader
from streamer_toolbox.core.events.role_loading import RoleLoading
from streamer_toolbox.gui.components.role_loading_panel import RoleLoadingPanel
from streamer_toolbox.gui.components.secrets_login_panel import SecretsLoginPanel
from streamer_toolbox.gui.pages.unlock_page import UnlockPage
from streamer_toolbox.gui.services.secrets_lock_middleware import UNLOCK, SecretsLockMiddleware
from streamer_toolbox.core.system.start_once import StartOnce
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.files.move_once import move_once
from streamer_toolbox.core.flows.debug_actions import DebugActions
from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.flows.timer_clock import TimerClock
from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.history.history_actions import HistoryActions
from streamer_toolbox.core.learn.learn_library import LearnLibrary
from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe
from streamer_toolbox.core.points.local_point_bank import LocalPointBank
from streamer_toolbox.core.points.point_actions import PointActions
from streamer_toolbox.core.points.point_earner import PointEarner
from streamer_toolbox.core.points.point_rules import PointRules
from streamer_toolbox.core.points.point_store import PointStore
from streamer_toolbox.core.security.login_throttle import LoginThrottle
from streamer_toolbox.core.security.remote_access import RemoteAccess
from streamer_toolbox.core.security.signed_in_devices import SignedInDevices
from streamer_toolbox.core.system.toolbox_restart import ToolboxRestart
from streamer_toolbox.core.system.toolbox_update import ToolboxUpdate
from streamer_toolbox.core.testing.test_gate import TestGate
from streamer_toolbox.core.testing.test_inventory import TestInventory
from streamer_toolbox.core.testing.test_list import TestList
from streamer_toolbox.core.testing.test_view import TestView
from streamer_toolbox.core.tips.tip_actions import TipActions
from streamer_toolbox.core.system.settings_backup import UPGRADES, SettingsBackup
from streamer_toolbox.core.system.upgrade_backup_policy import UpgradeBackupPolicy
from streamer_toolbox.core.upgrades.accounts_upgrade import AccountsUpgrade
from streamer_toolbox.core.upgrades.settings_upgrades import SettingsUpgrades
from streamer_toolbox.core.upgrades.settings_version import SETTINGS_VERSION
from streamer_toolbox.core.upgrades.youtube_accounts_upgrade import YouTubeAccountsUpgrade
from streamer_toolbox.core.upgrades.rumble_accounts_upgrade import RumbleAccountsUpgrade
from streamer_toolbox.connections.rumble_connection import MOVED as RUMBLE_MOVED
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.channel_lookup import ChannelLookup
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.latest_followers import LatestFollowers
from streamer_toolbox.core.widgets.missed_subscribers import MissedSubscribers
from streamer_toolbox.core.widgets.streamelements_cleaner import StreamElementsCleaner
from streamer_toolbox.core.widgets.streamelements_elements import StreamElementsElements
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.streamelements_media import StreamElementsMedia
from streamer_toolbox.core.widgets.streamelements_session import StreamElementsSession
from streamer_toolbox.core.widgets.subscriber_count import SubscriberCount
from streamer_toolbox.core.widgets.widget_helpers import WidgetHelpers
from streamer_toolbox.core.widgets.widget_hub import LOADED as WIDGET_LOADED, WidgetHub
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.alerts_tool.alerts_tool import AlertsTool
from streamer_toolbox.gui.components.events_tool.events_tool import EventsTool
from streamer_toolbox.gui.components.app_shell import AREAS, AppShell
from streamer_toolbox.gui.components.box_filter_panel import BoxFilterPanel
from streamer_toolbox.gui.components.flow_editor.action_picker import ActionPicker
from streamer_toolbox.gui.components.event_recording_panel import EventRecordingPanel
from streamer_toolbox.gui.components.test_view_panel import TestViewPanel
from streamer_toolbox.gui.components.flow_editor.trigger_catalog import group_of
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_KINDS
from streamer_toolbox.gui.components.header_notice import HeaderNotice
from streamer_toolbox.gui.components.plugin_listing_panel import PluginListingPanel
from streamer_toolbox.gui.components.update_panel import UpdatePanel
from streamer_toolbox.plugins.plugin_installer import PluginInstaller
from streamer_toolbox.plugins.listing_addresses import FILE_NAME as LISTINGS_FILE
from streamer_toolbox.plugins.listing_addresses import ListingAddresses
from streamer_toolbox.plugins.plugin_listings import PluginListings
from streamer_toolbox.gui.components.overlay_source import OverlaySource
from streamer_toolbox.gui.components.points_tool.points_tool import PointsTool
from streamer_toolbox.gui.components.twitch_tool.twitch_tool import TwitchTool
from streamer_toolbox.gui.components.import_tool.import_tool import ImportTool
from streamer_toolbox.gui.components.import_tool.streamelements_importer import StreamElementsImporter
from streamer_toolbox.gui.components.widgets_tool.designer_tool import DesignerTool
from streamer_toolbox.gui.components.widgets_tool.widgets_tool import WidgetsTool
from streamer_toolbox.gui.pages.connections_page import ConnectionsPage
from streamer_toolbox.gui.pages.flow_editor_page import FlowEditorPage
from streamer_toolbox.gui.pages.flows_page import FlowsPage
from streamer_toolbox.gui.components.live_deck.live_deck_view import BUTTONS_ONLY
from streamer_toolbox.gui.pages.learn_page import LearnPage
from streamer_toolbox.gui.pages.live_page import LivePage
from streamer_toolbox.gui.pages.login_page import LoginPage
from streamer_toolbox.gui.pages.overlay_page import OverlayPage
from streamer_toolbox.gui.pages.plugins_page import PluginsPage
from streamer_toolbox.gui.pages.settings_page import SettingsPage
from streamer_toolbox.gui.components.export_panel import ExportPanel
from streamer_toolbox.core.exports.export_finder import ExportFinder
from streamer_toolbox.core.exports.export_importer import ExportImporter
from streamer_toolbox.gui.pages.tools_page import ToolsPage, tool_slug
from streamer_toolbox.gui.pages.variables_page import VariablesPage
from streamer_toolbox.gui.services.activity_log import ActivityLog
from streamer_toolbox.gui.services.message_log import MessageLog
from streamer_toolbox.gui.services.notify_catcher import NotifyCatcher
from streamer_toolbox.gui.components.debug_list import DebugList
from streamer_toolbox.gui.components.info_bar import InfoBar
from streamer_toolbox.gui.services.nicegui_confirm_service import NiceGuiConfirmService
from streamer_toolbox.gui.services.nicegui_message_service import NiceGuiMessageService
from streamer_toolbox.gui.services.nicegui_plugin_context import NiceGuiPluginContext
from streamer_toolbox.gui.services.open_pages import OpenPages
from streamer_toolbox.gui.services.remote_login_middleware import RemoteLoginMiddleware
from streamer_toolbox.gui.services.ui_registry import UiRegistry
from streamer_toolbox.gui.services.widget_import_target import WidgetImportTarget
from streamer_toolbox.plugins.plugin_loader import PluginLoader
from streamer_toolbox.plugins.plugin_power import PluginPower
from streamer_toolbox.plugins.plugin_switches import PluginSwitches
from streamer_toolbox.plugins.plugin_template import PluginTemplate

log = logging.getLogger("streamer_toolbox")


BOX_CATEGORY = {"vtube_studio": "vts"}  # connection id → its boxes' category, where they differ


def assemble(args: argparse.Namespace, config: ToolboxConfig) -> tuple[TestGate, ToolboxRestart]:
    """Puts the whole toolbox together (connections, boxes, flows, pages) without starting it: nothing
    connects and no port is opened before ui.run. __main__ runs it; devtools/tested only reads what is in it."""
    actions = ActionRegistry()
    parked = set() if shows_wip(config.tables) else set(WIP_BOXES)
    actions.park(parked)
    gate = TestGate(TestList())
    test_view = TestView(gate.tested, app.storage.general)  # what he sees of it (Settings → What you see)
    ui_registry = UiRegistry()
    pages = OpenPages()
    confirm = NiceGuiConfirmService(pages)
    # the info bar and its Debug list (his round 81): every message, flow run and box error
    messages = MessageLog(args.config.parent / "cache" / "messages.json")
    app.on_shutdown(messages.save)
    activity = ActivityLog(on_add=messages.activity)
    catcher = NotifyCatcher(messages)
    catcher.install()
    shell = AppShell(ui_registry, pages)

    def info_bar() -> None:
        bar = InfoBar(messages)
        bar.build()
        catcher.attach(bar)

    shell.info_bar = info_bar
    secrets = SecretsFolder(args.config.parent)  # tokens, keys and logins: config/secrets/
    # one login per Twitch account, config/secrets/twitch/<login>.json, the main one in [twitch] main_account
    # (his plan of 2026-11-05: docs/PLAN_multi_accounts.md)
    twitch_tokens = AccountTokens(secrets.folder / "twitch", lambda file: secrets.path(f"twitch/{file}"),
                                  lambda: twitch.settings.get("main_account", ""), lambda name: set_twitch_main(name))
    # every event that names a viewer gets their role (only chat tells it): the role filter of the triggers
    roles = RoleBook(lambda: (twitch_tokens.load().user_id if twitch_tokens.load() else ""))
    events = EventBus(roles.fill)
    plugin_switches = PluginSwitches(args.config.parent / "plugins_off.json")
    power = PluginPower(plugin_switches, lambda: loader.plugins)  # off stops everything of a plugin (round 57)
    loader = PluginLoader(args.plugins, lambda plugin_id, folder: NiceGuiPluginContext(
        plugin_id, actions, ui_registry, confirm, shell.frame, folder, args.config.parent, events, secrets,
        lambda: not power.is_off(plugin_id)))
    ui_registry.is_off = power.is_off
    actions.guard(power.why_not)
    loader.load_all(config.plugins_enabled)
    ui_registry.category_titles.update({pid: m.name for pid, m in loader.manifests.items()})

    port = args.port or config.port
    boxes = args.config.parent / "boxes"  # what a box saves for itself: boxes/<program>/<box>/ (his sorting, round 43)
    move_once(args.config.parent / "box_values" / "vts_animation", boxes / "vts" / "animation")
    events.subscribe(CommonEvents(events).handle)
    last_events = LastEvents(args.config.parent / "cache" / "last_triggers")
    events.subscribe(last_events.handle)
    app.on_shutdown(last_events.flush)
    recording = EventRecording(args.config.parent / "cache" / "events", app.storage.general)  # Settings: off by default
    events.subscribe(recording.handle)

    def raw_event(kind: str, message: dict) -> None:
        last_events.raw(kind, message)
        recording.raw(kind, message)

    def save_twitch(values: dict) -> None:
        """A Twitch setting the tab changed (its accounts): into toolbox.toml [twitch] and into the connection."""
        ConfigTableWriter(args.config).save("twitch", values)
        twitch.configure({**twitch.settings, **values})

    def set_twitch_main(name: str) -> None:
        save_twitch({"main_account": name})

    twitch = TwitchConnection(config.tables.get("twitch", {}), twitch_tokens, events, folder=args.config.parent,
                              raw=raw_event, save_settings=save_twitch)

    probe = Mp4HeaderProbe()

    def wants_key(name: str) -> bool:
        """Only keys a flow's Key trigger names become events (flows is set further down, before any key)."""
        return any(trigger.matches(KEY_PRESSED, {"key": name}) for flow in flows.all() for trigger in flow.triggers)

    mixitup = MixItUpConnection(config.tables.get("mixitup", {}))
    heart = HeartRate(events)
    if not left_out(HEART_RATE):
        heart.add_to(actions)
    built_in = BuiltInConnections(config.tables, config.obs, args.config.parent, events, secrets, raw_event,
                                  config_file=args.config)
    connections = ConnectionManager([connection for connection in [
        *built_in.build(
            probe, twitch, twitch_tokens, mixitup, heart, wants_key,
            lambda: toolbox_deck(actions, config.callers, port)),
        *ui_registry.connections,  # a plugin's own (ctx.add_connection)
    ] if connection.id not in LEFT_OUT], ConfigTableWriter(args.config),
        paused=power.is_off)
    power.connections = connections
    for connection in ui_registry.connections:
        connection.configure(config.tables.get(connection.id, {}))
    for connection in connections.all():
        connection.add_actions(actions)
        for box in connection.boxes():
            actions.add_box(box, connection.id)
        accounts = connection.account_choice()
        if accounts is not None:  # several accounts: its boxes get an Account field (docs/PLAN_multi_accounts.md)
            actions.accounts_for(connection.id, *accounts)
    actions.sort_into(lambda: {category: SERVICES for c in connections.all()
                               for category in (c.id, BOX_CATEGORY.get(c.id, c.id))}
                      | {HEART_RATE: SERVICES}  # HypeRate's and Pulsoid's box
                      | {plugin_id: PLUGINS for plugin_id in loader.loaded})
    variables = VariableStore(args.config.parent / "variables", args.config.parent / "variables.json")
    LogicActions(variables).add_to(actions)
    DebugActions(activity.add).add_to(actions)
    chat_memory = ChatMemory()
    events.subscribe(chat_memory.handle)
    chat_memory.add_to(actions)


    def switched_off() -> dict[str, str]:
        """Box category → program, for the connections and plugins that are off: their boxes stay out of the
        Add box window and their triggers out of Add trigger. Nothing is left out while "Disconnected" is ticked
        (Settings → What you see)."""
        if test_view.disconnected:
            return {}
        off = {BOX_CATEGORY.get(c.id, c.id): c.title for c in connections.all() if not c.settings["enabled"]}
        plugins_off = {pid: f"{loader.manifests[pid].name if pid in loader.manifests else pid} (plugin)"
                       for pid in plugin_switches.off() if pid in loader.loaded}
        return off | plugins_off

    box_filters = BoxFilterStore(args.config.parent / "box_filters.json")
    OwnBoxes(variables, probe, NiceGuiMessageService(pages), confirm,
             config.tables.get("sound", {}).get("folder"), boxes).add_to(actions)
    # the alerts before the flows; each alert plays on its event (Overlay → Events, its Send box)
    alert_queue = AlertQueue()
    alert_store = AlertStore(args.config.parent / "alerts.json")
    AlertActions(alert_queue).add_to(actions)
    alert_backup = AlertBackup(args.config.parent / "alert_backup.json", alert_store, alert_queue)

    async def keep_alerts() -> None:
        alert_backup.start()  # before the connections: what was kept plays first
    runner = FlowRunner(actions, variables)
    flows = FlowLibrary(FlowStore(args.config.parent / "flows"), FlowStore(args.config.parent / "flow_templates"),
                        runner, actions)
    flows.load()
    async def refund(data: dict) -> None:
        await twitch.finish_redeem(data.get("reward_id", ""), data.get("redemption_id", ""), refund=True)

    events.subscribe(FlowTriggerRouter(flows, runner, activity.add, refund).handle)
    widget_store = WidgetStore(args.config.parent / "widgets")

    def channel_info() -> dict[str, str]:
        """The streamer's Twitch login name and id, for widgets (their code checks "is this the streamer?")."""
        token = twitch_tokens.load()
        twitch_side = {"username": token.login, "providerId": token.user_id} if token else {}
        return {**twitch_side, "id": streamelements_import.account_id()}

    streamelements_import = StreamElementsImport(secrets.path("streamelements_token.txt"))
    history = EventHistory(args.config.parent / "history" / "events.jsonl")
    HistoryActions(history).add_to(actions)
    widget_hub = WidgetHub(WidgetSession(args.config.parent / "cache" / "widget_session.json", history),
                           channel_info)
    widget_fallback = StreamElementsFallback(config.tables.get("widgets", {}), ConfigTableWriter(args.config))
    events.subscribe(widget_hub.handle)  # the session data only: what a widget shows comes from flows
    widget_hub.on_loaded = lambda name, preview: events.publish(WIDGET_LOADED, {"widget": name, "preview": preview})
    missed_subs = MissedSubscribers(twitch.helix, channel_info, widget_hub.session, history,
                                    args.config.parent / "history" / "subscribers.json")
    events.subscribe(missed_subs.handle)
    # Overlay → Events (his round 78): widgets and alerts get event types; one Send box and flow per type
    event_types = EventTypeStore(args.config.parent / "event_types.json")
    event_flows = EventFlows(flows, event_types)
    event_users = EventUsers(event_types, widget_store, alert_store, event_flows)
    conversion = EventConversion(event_types, widget_store, alert_store, flows)
    def upgrade_backup(old: int, new: int) -> Path:
        """The settings folder before an upgrade (his rule, 2026-11-05): backups/upgrades/, the last 5 and the
        first of every day kept."""
        backup = SettingsBackup(args.config.parent, sub=UPGRADES)
        copy = backup.make(f"settings-v{old}-before-v{new}")
        backup.prune(UpgradeBackupPolicy())
        return copy

    upgrades = SettingsUpgrades(args.config, [  # the settings folder's version: docs/SETTINGS_CHANGES.md
        EventsUpgrade(conversion),
        AccountsUpgrade(lambda: twitch_tokens.move_single_file(OAuthTokenStore(secrets.path("twitch_token.json"))),
                        event_types, ConfigTableWriter(args.config)),
        YouTubeAccountsUpgrade(lambda: built_in.youtube_tokens.move_single_file(
            OAuthTokenStore(secrets.path("youtube_token.json")))),
        RumbleAccountsUpgrade(lambda: built_in.rumble_keys.move_single_file(
            secrets.path("rumble_address.txt"), RUMBLE_MOVED))], back_up=upgrade_backup)
    for line in upgrades.run() + conversion.leftovers():
        log.info("settings upgrade %s", line)
    flows.upgrade = upgrades.flow  # an imported flow from an older toolbox gets the same upgrades
    if upgrades.newer:  # his answer of 2026-11-01: shown next to the toolbox's name
        shell.notices["settings"] = HeaderNotice(
            "Newer settings", f"These settings are from a newer toolbox (settings version {upgrades.version}, "
            f"this one knows up to {SETTINGS_VERSION}).\n\nThe toolbox reads them as they are and changes "
            "nothing in them. Something made in the newer version may not work here.\n\nUse the newer "
            "toolbox again, or a copy of the settings from before.")
    if upgrades.failed:  # his rule: no upgrade without a backup before it
        shell.notices["settings"] = HeaderNotice(
            "Settings not upgraded", f"This toolbox needs its settings upgraded to version {SETTINGS_VERSION}, but "
            f"{upgrades.failed}.\n\nNothing in the settings was changed; the toolbox reads them as they are, so "
            "something may not work. The next start tries again (is the disk full, or a file open somewhere?).")
    for name in widget_store.names():  # widgets that never had inputs or events: the ones their code asks for
        event_users.give_events(name)
    event_users.start()  # alerts follow their events; each used event has its flow (made once)
    event_actions = EventActions(event_types, EventSender(event_types, widget_store, widget_hub, alert_store,
                                                          alert_queue), event_users.choices)
    event_actions.add_to(actions)

    def events_changed() -> None:
        event_actions.sync()
        event_users.follow_events()

    event_types.on_change = events_changed
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

    clock = TimerClock(flows, events)
    payouts: list[asyncio.Task] = []  # keeps the task alive

    # Settings → Viewer roles: Twitch's mod, VIP and sub lists into the role book, when he asks for it
    role_loading = RoleLoading(app.storage.general)
    role_loader = RoleLoader(roles, role_loading, TwitchRoleList(twitch.helix, twitch_tokens.load).read)

    async def start_payouts() -> None:
        payouts.append(asyncio.get_running_loop().create_task(role_loader.run()))
        payouts.append(asyncio.get_running_loop().create_task(earner.run()))
        payouts.append(asyncio.get_running_loop().create_task(look_for_missed_subs()))

    async def look_for_missed_subs() -> None:
        await asyncio.sleep(20)  # once Twitch is connected
        found = await missed_subs.check()
        if found:
            log.info("%d sub(s) came in while the toolbox was off", len(found))

    # with a login set (Settings → Login) nothing starts before the password was typed (UnlockPage)
    work = StartOnce([keep_alerts, connections.start_all, clock.start, start_payouts, power.start_all])

    async def start_unless_locked() -> None:
        if secrets.vault.unlocked:
            await work.run()
        else:
            log.info("locked: waiting for the login before anything starts")

    app.on_startup(start_unless_locked)
    app.on_shutdown(connections.stop_all)
    app.on_shutdown(power.stop_all)
    app.on_shutdown(clock.stop)

    # max_cache_age 0: a browser asks again each time (a 304 when unchanged), so a changed script counts at once;
    # with NiceGUI's hour a new button called a function the old cached file didn't have (round 63)
    app.add_static_files("/static", Path(__file__).resolve().parents[1] / "gui" / "static", max_cache_age=0)
    access = RemoteAccess(config.tables.get("api", {}), config.tables.get("access", {}),
                          ConfigTableWriter(args.config))
    devices = SignedInDevices(args.config.parent / "signed_in_devices.json")
    app.add_middleware(WidgetSandboxMiddleware)
    app.add_middleware(SecretsLockMiddleware, vault=secrets.vault)
    ui.page(UNLOCK, title=f"Log in · {APP_NAME}")(UnlockPage(secrets.vault, LoginThrottle(), work.run).build)
    app.add_middleware(RemoteLoginMiddleware, access=access, devices=devices, is_login_client=_is_login_client)
    ui.page("/login", title=f"Sign in · {APP_NAME}")(LoginPage(access, LoginThrottle(), devices).build)
    app.include_router(build_action_router(actions, CallerAuth(list(config.callers)), activity.add))
    app.include_router(build_overlay_router(alert_queue))
    app.include_router(build_widget_router(widget_store, widget_hub, WidgetPage(widget_hub.session, channel_info),
                                           ChannelLookup(twitch.helix, channel_info), widget_fallback,
                                           EmoteLookup(), LatestFollowers(twitch.helix, channel_info),
                                           SubscriberCount(twitch.helix, channel_info)))
    deck_images = DeckImages(args.config.parent / "deck_images")
    deck_images.folder.mkdir(parents=True, exist_ok=True)
    app.add_static_files(DECK_IMAGES_URL, deck_images.folder)
    deck_store = DeckStore(args.config.parent / "live_deck.json", flows.all)  # one: a save redraws open Live pages
    live_page = LivePage(actions, activity, deck_store, flows,
                         deck_images, lambda: ActionPicker(actions, filters=box_filters, switched_off=switched_off,
                                                           view=test_view, flow_only=False))
    shell.page("Live", "/", live_page.build, heading=False)
    shell.sub_items["/"] = live_page.side_items
    shell.no_overview.add("/")
    shell.bare("Live buttons", BUTTONS_ONLY, live_page.build_bare)
    shell.bare("Debug", "/debug", lambda: DebugList(messages).build(title=True))  # the info bar's pop-out window
    flows_page = FlowsPage(flows, actions, activity, runner)
    shell.page("Flows", "/flows", flows_page.build)
    shell.sub_items["/flows"] = flows_page.side_items
    shell.side_tools["/flows"] = flows_page.side_tool
    def trigger_accounts(kind: str) -> list[str]:
        """The accounts of the trigger's connection whose events come in now (Twitch with several); for a
        common trigger (any platform) those of every connection."""
        owner, dot, _ = kind.partition(".")
        return [name for c in connections.all() if not dot or c.id == owner for name in c.listening_accounts()]

    shell.page("Edit flow", "/flows/edit", FlowEditorPage(flows, actions, runner, variables,
                                                            BoxValueFiles(boxes),
                                                            {"twitch.redeem": twitch.reward_choices},
                                                            box_filters, switched_off, last_events,
                                                            test_view, trigger_accounts).build)
    shell.page("Variables", "/variables", VariablesPage(variables, flows).build)
    ui_registry.tools.insert(0, ("toolbox", "Twitch", "live_tv", "Your channel point rewards (and more Twitch things "
                                 "later)", lambda: TwitchTool(twitch, flows).build()))
    ui_registry.tools.insert(1, ("toolbox", "Points", "toll", "Your own currency: how viewers earn it, and who has "
                                 "how much", lambda: PointsTool(points, earner, mixitup_points).build()))

    overlay_source = OverlaySource(actions)
    ui_registry.importers.insert(0, ("toolbox", StreamElementsImporter(
        streamelements_import, StreamElementsElements(streamelements_import),
        StreamElementsSession(streamelements_import, history=history), widget_store, widget_hub,
        StreamElementsCleaner(widget_store, StreamElementsMedia(widget_store), WidgetHelpers(widget_store)))))
    shell.page("Overlay", "/overlays", OverlayPage(
        AlertsTool(alert_store, alert_queue, flows, event_types, event_users),
        WidgetsTool(widget_store, widget_hub, overlay_source, port, event_types, event_users, event_flows,
                    widget_fallback),
        ImportTool(ui_registry.importers_on, WidgetImportTarget(widget_store, event_users)),
        EventsTool(event_types, event_users, event_flows), alert_queue, alert_backup, overlay_source, port,
        DesignerTool(widget_store, widget_hub, event_users)).build)
    tools_page = ToolsPage(ui_registry, test_view)
    shell.page("Tools", "/tools", tools_page.build)
    shell.sub_items["/overlays"] = [("Alerts", "/overlays?show=alerts", "campaign"),
                                    ("Widgets", "/overlays?show=widgets", "widgets"),
                                    ("Widget editor", "/overlays?show=designer", "design_services", True),
                                    ("Events", "/overlays?show=events", "bolt"),
                                    ("Import", "/overlays?show=import", "file_download")]
    shell.sub_items["/tools"] = lambda: [(title, f"/tools?show={tool_slug(title)}", icon or "handyman")
                                         for _, title, icon, *_ in tools_page.shown()]
    default_flows = DefaultFlows(flows)
    connections_page = ConnectionsPage(config, args.config, ui_registry, connections, test_view, default_flows)
    shell.sub_items["/connections"] = lambda: [("Toolbox", "/connections?show=toolbox", "lan")] + [
        (c.title, f"/connections?show={c.id}", c.icon) for c in connections_page.shown()]
    shell.page("Connections", "/connections", connections_page.build)
    restart = ToolboxRestart(app.shutdown, available=args.child)
    # the toolbox's own update (next release plan, part 1): a new version shows next to its name
    toolbox_folder = Path(__file__).resolve().parents[3]  # the one with src/ (and python/ in a download)
    update_settings = config.tables.get("update", {})  # [update] check, channel (Settings → General)
    toolbox_update = ToolboxUpdate(toolbox_folder, args.config.parent / "cache" / "update",
                                   settings=args.config.parent, channel=str(update_settings.get("channel", "release")))
    # Plugins → Get plugins (next release plan, part 4): several listing files, the toolbox installs from them;
    # test versions of plugins follow the same "Which versions" as the update
    listing = PluginListingPanel(PluginListings(ListingAddresses(args.config.parent / LISTINGS_FILE),
                                                channel=lambda: toolbox_update.channel),
                                 PluginInstaller(args.plugins, args.config.parent / "cache" / "plugins"), restart,
                                 shell.notices, lambda: update_panel.checking)  # "Plugin updates (n)" at the start
    plugins_page = PluginsPage(lambda: (loader.loaded, loader.failed, loader.disabled, loader.manifests),
                               ui_registry, plugin_switches, PluginTemplate(args.plugins), power, listing)
    shell.page("Plugins", "/plugins", plugins_page.build)
    shell.sub_items["/plugins"] = plugins_page.side_items
    learn_page = LearnPage(LearnLibrary(more=ui_registry.learn_folders_on), default_flows)
    shell.page("Learn", "/learn", learn_page.build)
    shell.sub_items["/learn"] = learn_page.side_items
    update_panel =UpdatePanel(toolbox_update, restart, ConfigTableWriter(args.config),
                               bool(update_settings.get("check", True)), shell.notices)
    app.on_startup(update_panel.start)
    app.on_startup(listing.start)
    settings_page = SettingsPage(args.config, ui_registry, access, devices, port,
                                restart, BoxFilterPanel(box_filters, actions),
                                TestViewPanel(test_view, lambda: gate.items()),
                                RoleLoadingPanel(role_loading, role_loader), EventRecordingPanel(recording),
                                SecretsLoginPanel(secrets.vault, str(secrets.folder)), update_panel,
                                ExportPanel(ExportFinder(flows, alert_store, widget_store, event_types, variables,
                                                         deck_store, deck_images, actions),
                                            ExportImporter(flows, alert_store, widget_store, event_types, variables,
                                                           deck_store, deck_images, actions,
                                                           args.config.parent / "media", event_users.start)))
    shell.page("Settings", "/settings", settings_page.build)
    shell.sub_items["/settings"] = settings_page.sections

    def menu() -> list[tuple[str, str, list[tuple[str, str]]]]:
        """The side menu for the test record: every main tab with the pages below it. The tools and the
        connections are not pages here: they have rows of their own."""
        below = {"/flows": [("Edit flow", "/flows/edit")],
                 "/overlays": [(title, path) for title, path, *_ in shell.sub_items["/overlays"]],
                 "/connections": [("Toolbox", "/connections?show=toolbox")],
                 "/plugins": [(title, path) for title, path, _ in ui_registry.pages],
                 "/learn": [(title, path) for title, path, *_ in learn_page.side_items()],
                 "/settings": [(title, path) for title, path, _ in settings_page.sections()]}
        return [(title, path, below.get(path, [])) for title, path, _ in AREAS]

    gate.apply(actions, lambda: TestInventory(
        actions, [(c.id, c.title) for c in connections.all()], [title for _, title, *_ in ui_registry.tools],
        {kind: (entry[1], group_of(kind)) for kind, entry in TRIGGER_KINDS.items()}, BOX_CATEGORY, menu()).items())
    return gate, restart


def _is_login_client(client_id: str) -> bool:
    """Whether that open page is the login page: a device that isn't signed in may only use the socket for it."""
    client = Client.instances.get(client_id)
    return client is not None and client.page.path == "/login"

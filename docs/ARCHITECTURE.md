# Architecture

How the code is laid out, and where a new piece goes.

Rules: interfaces are `abc.ABC` classes in `core/interfaces/`, one per file; data are (frozen) dataclasses;
one class per file (tests and fakes too); pathlib; PEP 8. A folder holds one kind of thing; helpers go in a
sub folder named after what uses them.

## Folder map (`src/streamer_toolbox/`)

```
__main__.py              the start: arguments, the launcher (runs the toolbox as a child, restarts it), ui.run
assembly/                putting the toolbox together, without starting it: toolbox_assembly.assemble() (the
                         one place where the pieces are wired: connections, boxes, flows, pages),
                         BuiltInConnections (the list of connections, in the order of their tabs),
                         OwnBoxes (the boxes that belong to no program)
core/                    shared building blocks, no service-specific code
  interfaces/            every interface: Connection, VideoProbe, LayoutPolicy, SceneItemEditor,
                         ObsConnectionChecker, ConfirmService, MessageService, PageOpener, PluginContext,
                         ToolboxPlugin, SoundPlayer
  actions/               ActionRegistry (every runnable action by name), RegisteredAction, action descriptions;
                         JsonBoxes + JsonBox + JsonBoxField (boxes written as JSON: a folder of *.json, each box
                         one request with fields whose kinds are ValueKinds names; first user: connections/obs/
                         boxes/; plugins: ctx.add_json_boxes; docs/ai/code/action.md has the file's shape);
                         BoxFilter (a named pick of categories "obs", sub groups "obs/Media" and single boxes,
                         minus `without`), BoxFilterStore (the basic ones + his own in config/box_filters.json),
                         BoxFilterDraft (one being edited: boxes / whole groups in and out) for the Add box window;
                         wip_boxes (WIP_BOXES: boxes parked because they don't do what they should yet, with the
                         reason; ActionRegistry.park leaves them out of all(), get / run still know them;
                         `[wip] show = true` in toolbox.toml shows them)
  testing/               what has to be tested before a build offers it. TestItem (a page, trigger, box, tool
                         or connection, with its file in the record), TestInventory (all of them in the side
                         menu's order, from the registry and the lists main has), TestList (the record as text in
                         docs/tested/, in git, sorted like the menu: <tab>/page.md, flows/triggers/<program>.md,
                         flows/boxes/<category>/<group>.md, tools/<tool>.md, connections/<id>.md; per row
                         "AI checked" (the day Hex tried it), three checks, the day and a note; tested = all
                         three), release_marker (a build has the file tested_only.txt next to the code), TestGate
                         (what main asks: in a build it parks every untested box, leaves untested
                         connections / triggers out through left_out.leave_out, drops untested tools and gives
                         AppShell.left_out the untested pages' addresses (not in the menu, a line instead of
                         the page); in the project folder everything is on). The files are made by
                         devtools/tested, not at start, and ticked in its test window, not in the toolbox
  config/                ToolboxConfig + its dataclasses (reads config/toolbox.toml), ConfigTableWriter
  connections/           the framework around Connection: ConnectionBase, ConnectionManager,
                         ConnectionStatus, ConnectionState, SettingField, NotConnectedError
  layout/                box maths (pure)
  media/                 video size + length probing (Mp4HeaderProbe: tkhd / mvhd), VideoActions (video.info:
                         width, height, seconds, orientation); sound: MiniaudioSoundPlayer + SoundActions
  alerts/                Alert, AlertQueue (one alert at a time to every listening overlay page; an alert's
                         files get one-time names under /overlay/file/), AlertActions (alert.show / alert.clear),
                         AlertRule + AlertStore (config/alerts.json: per Twitch event on / text / picture / sound),
                         AlertLook (where on the screen, animations, sizes, colours; per rule, sent with the
                         alert), AlertPart (a piece of the words: text line, name, amount, their message; a rule
                         has a list of them, each in the stack or on the picture at its own spot), AlertVariation (another text /
                         picture / sound from an amount),
                         AlertRouter (EventBus → the rule → the queue; Test)
  widgets/               custom widgets in StreamElements' format (docs/WIDGETS.md): Widget, WidgetStore
                         (config/widgets/<name>/: the four parts, values.json, store.json), widget_events
                         (se_event: a toolbox event as their listener + event), WidgetSession (their "session
                         data"), WidgetHub (EventBus → every open widget page; Test, reload), WidgetPage (builds
                         the page: field values filled in, widget.js, his code); example/ = the example widget;
                         WidgetActions (widget.send_event: a flow sends widgets any event);
                         StreamElementsImport (the custom widgets of one of his StreamElements overlays, through
                         their API, read only); StreamElementsElements (one of his "Elements" = a settings
                         file without code: becomes a widget whose JS hands the settings to
                         gui/static/overlay/element.js, its files copied into the widget's media/ folder);
                         WidgetSession keeps the latest / recent / totals in config/cache/widget_session.json;
                         StreamElementsMedia (the files a widget names at StreamElements' servers, kept in its
                         media folder; streamelements_media.json; the widget's stand-in serves the copies),
                         WidgetHelpers (the outside scripts / style sheets a widget's HTML loads, kept in its
                         media folder; helpers.json; the page then loads the copies),
                         WidgetSafety (per widget, safety.json: the page's sandbox and its allowed hosts, as
                         response headers; api/widget_sandbox_middleware lets the sandboxed page reach its own
                         routes); LatestFollowers (Twitch's follower list → the session data)
  tips/                  TipActions: tip.fire = "Tip came in", the way in for tips from any service (a flow,
                         SAMMI, the API) → the `tip` event: Tip trigger, Tip alert, widgets' tip-latest
  values/                ValueKind (a kind of value a box field can hold, by name: how it is typed, what is
                         sent), ValueKinds (the global ones: text, number, whole_number, yes_no, color, list,
                         object, file, folder, image, sound, video, media; a connection or plugin adds its
                         special ones, e.g. "obs.scene"). Used by the boxes written as JSON
  files/                 FileActions (file.write_text / read_text, flow only); FileBrowser (a folder's sub
                         folders and files by ending → FolderListing, where the file window opens, places to jump
                         to), file_types (VIDEO / AUDIO / IMAGE / MEDIA_TYPES, ANY_FILE, FOLDER)
  security/              RemoteAccess (who may open the pages: this PC always, other devices with the [access]
                         password when [api] host = 0.0.0.0), PasswordHash (salted PBKDF2), LoginThrottle, SignedInDevices
                         (signed-in browsers by session cookie id, config/signed_in_devices.json)
  popups/                PopupActions: popup.message (Show message) and popup.ask (Ask yes/no; ports yes / no /
                         no_answer) on every open toolbox screen, through MessageService and ConfirmService
  data/                  ListActions (list.add / remove / contains / size / get / random), JsonActions (json.read /
                         write), SplitActions (data.split = Split data: one output per field, as its kind),
                         box_value helpers (to_list, to_bool, same = If-style equality, kind_of / understand /
                         to_kind for Split's number / text / yes/no / list / object); ObjectActions (object.get /
                         has / keys / values / set / remove / build: on wired objects, changing gives a new one),
                         TextActions (text.split / join / replace / length / case / trim)
  system/                ProgramActions (system.run = Run program: output / exit code / timeout, flow only),
                         TimeActions (time.now = Date and time, time.since); ToolboxLauncher, ToolboxRestart,
                         ParentWatch (see "Starting and restarting")
  web/                   HttpActions: web.request (GET/POST/..., query, JSON body, headers → {status, ok, body},
                         JSON body already read; httpx transport injectable for tests)
  events/                EventBus: events (twitch.redeem, twitch.chat, timer) go to every listener as tasks;
                         EVENT_FIELDS: the data keys each event gives (Start box dots; keep in step with publish())
  flows/                 Flow = FlowNode boxes + FlowWire wires (+ inputs, triggers); FlowStore (one .toml per flow,
                         also templates; reads old [[steps]] files as a chain); FlowRunner (runs from Start along
                         wires, parallel per output, If picks then/else, Repeat fires a list of ports in turn,
                         fills ${var.x} ${input.x} ${event.x} ${get.action} ${box.n3.x}, save_as); box_wire helpers
                         (${box...} data wires); FlowOutline (graph → SAMMI-like list);
                         LogicActions (If, Repeat, For each, Wait, Random, Set / Add to variable, Set field); FlowLibrary (keeps
                         flow.<name> actions in step with the files; export / import a flow as .toml text); FlowTriggerRouter (EventBus → flows whose
                         triggers match, * wildcards); TimerClock (timer triggers, "every N seconds")
  history/               EventHistory (the toolbox's own dated record of follows, subs, cheers, raids, tips:
                         config/history/events.jsonl; sums per session / week / month / all time, top
                         givers), HistoryActions (boxes)
  events/common_events   CommonEvents: each platform's event also as the common one (chat, follow, sub,
                         resub, gift, cheer, raid, redeem, online, offline) with `platform` + `source`
  points/                the toolbox's own currency: PointStore (config/points/points.json, per viewer and
                         platform), PointRules ([points] in toolbox.toml), PointEarner (EventBus → chatters
                         paid every few minutes, bonuses, the points chat command), PointActions (boxes)
  variables/             VariableStore: the variables, one JSON file (config/variables.json)
  connections/left_out   LEFT_OUT: the connections this copy leaves out (empty in the project; a build
                         adds the untested ones at start, see core/testing), and
                         which events go with a connection (hides triggers of off / left-out ones)
  (plugins)              PluginContext (core/interfaces) is a plugin's only door: actions with everything a
                         box can have, ONE connection (collected in UiRegistry.connections, joined to the
                         built-in ones in assembly/BuiltInConnections, configured from its [<id>] table), triggers (written
                         into EVENT_FIELDS and TRIGGER_KINDS at load), publish / on_event on the EventBus.
                         plugins/example/ is the guided tour of all of it
connections/             ONLY the connection classes, one per service
  obs_connection.py  sammi_connection.py  mixitup_connection.py  vts_connection.py  twitch_connection.py
  streamelements_connection.py  streamlabs_connection.py  rumble_connection.py  youtube_connection.py
  websocket/             SocketMessageSender: open, send one text, close (VNyan, Warudo); RequestSocket (a
                         websocket that stays open and talks JSON: requests matched to their answers by an
                         id, the program's own messages, connects again by itself); LineConnection (the
                         connection class around one RequestSocket: start / stop / test / _ask)
  tits/                  TitsActions (throw an item, activate a trigger, by name). The connection has two
                         websockets: /websocket for requests, /events → tits.hit / trigger_started / _ended
  streamerbot/           StreamerbotActions (run an action by name, code trigger, get global, write in
                         chat), streamerbot_events (the password answer; an event → streamerbot.event)
  firebot/               FirebotActions (run a preset effect list by name, custom variables, counters) over
                         Firebot's web API. Send only
  lumia/                 LumiaActions (command, alert, colour, anything else) over Lumia's Send API; the
                         connection's websocket → lumia.event
  voicemod/              VoicemodActions (voice, random voice, soundboard, switches) over its Control API
  heartrate/             HeartRate: the last heart rate whichever service told it (pulsoid_connection.py,
                         hyperate_connection.py), the `heartrate` event, the heartrate.get box
  crowdcontrol_connection.py  listens to a streamer's public topic on Crowd Control's websocket →
                         crowdcontrol.effect (no sub folder: it has no boxes)
  discord/               DiscordActions: a message into a channel through its webhook
  tiltify/               TiltifyFeed (logs in as his application, asks for a campaign's new donations
                         again and again → tiltify.donation; not a tip)
  vnyan/                 VNyanActions: a named message to VNyan's node graph (its WebSocket node; its API
                         Message node over the web API on 8069). Send only
  warudo/                WarudoActions: a named action to a Warudo blueprint (On WebSocket Action node, port
                         19190). Send only; the message's shape is not confirmed with the real program
  veadotube/             VeadotubeInstances (finds the running veadotube mini by the files it keeps),
                         VeadotubeClient (its websocket: the avatar's states, listens for changes →
                         veadotube.state), VeadotubeActions (set / show for a while / stack, by name)
  streamsocket/          StreamSocketClient (the Twitch extension "StreamSocket Events": its server's
                         websocket, secret check, the server's connection checks; a redemption →
                         streamsocket.event)
  youtube/               YouTubeAuth (Google login; reading only, writing in chat is his switch), YouTubeApi
                         (his channel, the live stream's chat, its messages, send), YouTubeChat (waits for a
                         stream, then asks the chat again and again; quota), youtube_events (a chat message →
                         youtube.chat / superchat / supersticker / member / member_milestone / gift_members;
                         money also → tip). The login uses the shared pieces in oauth/
  rumble/                RumbleFeed (asks Rumble's Live Stream API every few seconds; the address holds the
                         key), RumbleNews (what is new in an answer → rumble.chat / follow / sub / gift /
                         rant / online / offline; a rant also → tip)
  streamelements/        AstroClient (their websocket: subscribe to the activities with the JWT, reconnect),
                         astro_events (an activity → streamelements.activity, a tip also → tip)
  streamlabs/            StreamlabsSocket (their socket: Engine.IO 3 on a plain websocket, pings, reconnect),
                         streamlabs_events (an event → streamlabs.activity with its platform; a donation,
                         Super Chat or Super Sticker also → tip)
  obs/                   what ObsConnection uses: websocket client wrapper, checker, scene item editor, fit actions,
                         source actions (show/hide, volume, Media Source: set file, set size, restart/play/pause/
                         stop), request actions (obs.request = SAMMI's raw request, flow only; ObsProtocol +
                         protocol/<category>.json: requests by category, data template, field hint). Newer action classes
                         share ObsRequests (request + pickers): ObsMediaPlayback (Play video once: own source,
                         removed after; polls the media state), ObsAudioActions, ObsOutputActions,
                         ObsFilterActions, ObsNewSourceActions, ObsSceneActions. Play video once also comes
                         in parts: obs.new_media_source, obs.place_like, obs.wait_media_end.
                         ObsPlacement (a spot + box in a scene) and ObsPlacementActions (Place source, Get source
                         place, the place marker he drags in OBS)
  mixitup/               MixItUpActions: Mix It Up's Developer API v2 as boxes (names in, IDs looked up)
  sammi/                 what SammiConnection uses: deck builder, toolbox deck, deck CLI (python -m ...connections.sammi)
                         SammiDeckList (SAMMI's own decks + buttons via getDeckList, for button / deck dropdowns)
  vtube_studio/          what VtsConnection uses: VTS API client, positions and their store, VtsItemActions (items and
                         pins), VtsExpressionActions, VtsHotkeyActions, VtsLookActions (tint,
                         physics, parameters, visual effects; physics / parameters are re-sent while they hold)
  oauth/                 what every browser login shares (Twitch, YouTube): OAuthCodeListener (one-shot on the
                         redirect port), OAuthToken, OAuthTokenStore (one file per service next to the settings)
  keyboard/              what KeyboardConnection uses: PynputKeyListener (the system-wide key listener),
                         KeyName (a key press as the name a trigger uses, "ctrl+k")
  twitch/                what TwitchConnection uses: TwitchAuth (login, refresh, validate), TwitchApi (Helix),
                         EventSubClient (websocket)
                         TwitchChannelActions (channel info, title, category, ads, users, followers; via
                         TwitchApi.helix)
api/                     the HTTP API (POST /action/<name>), callers, tokens, allowlists; overlay_router: the
                         alerts overlay for OBS's Browser source (GET /overlay/alerts = gui/static/overlay/, its
                         websocket, the alert files) and widget_router (/overlay/widget/<name>: a shell holding the page (.../page) in a frame, its
                         websocket, his media files, the widget's own store). No tokens: the login gate guards
                         them like the pages
gui/
  pages/                 one file per page: Live, Flows, Edit flow, Variables, Overlay (the overlay's address,
                         Add it to OBS, a preview frame, tabs: Alerts, Widgets), Tools, Connections, Plugins,
                         Settings,
                         Login (other devices only)
  components/            reusable pieces: AppShell (menu/layout; `sub_items` = a fold-out list under a menu
                         area: the row opens the area's main view, its arrow folds the list; Connections,
                         Overlay, Tools, Settings: main view = cards, `?show=<part>` = that part alone), ConnectionPanel (one connection's settings),
                         FileDialog (the file window of a box's file field), BoxFilterPanel (Settings → Box
                         filters) + BoxFilterDialog (every box left, the filter's boxes right)
    flow_editor/         FlowEditor and what it uses: drafts (mutable copies), NodeEditor (one box's form), BoxDots (what a box takes and gives: fields, data
                         dots, kinds, the wires a field may take, its summary; no drawing),
                         ParamInput (value / variable / Live value / flow input / wire from a box),
                         SplitFieldsInput (Split data's outputs + Find fields), ActionPicker (Add menu with search),
                         FlowListView (SAMMI-like list), FlowBoxView + DrawflowGraph (boxes and wires),
                         AnimationInput / AnimationDialog / AnimationMap (a box's own model animation)
    twitch_tool/         TwitchTool (Tools page, first tab; sub tabs, one class each): RedeemsTab (every reward,
                         its flows, Make a flow, edit / pause / on / delete the toolbox's own) + RewardDialog.
                         Talks to TwitchConnection through RewardManager (core/interfaces; TwitchReward in
                         connections/twitch). Twitch: only rewards this app made may be changed or refunded
    alerts_tool/         AlertsTool (the Alerts tab of the Overlay page: a short block per event: on / off,
                         summary, Test, Settings) and AlertSettingsDialog (everything about one alert: the
                         overlay page in a frame with ?edit=1, fed by postMessage; dragging a piece or the
                         picture there posts its spot back; Advanced switch for the rest)
    widgets_tool/        WidgetsTool (the Widgets tab), WidgetDialog (preview, test events, settings, code),
                         WidgetFieldsForm (settings drawn from FIELDS)
    points_tool/         PointsTool (Tools page, Points tab: the switch, name and numbers, the viewers' list)
    live_deck/           LiveDeckView (the Live page's deck: page tabs, button grid, edit mode, presses) and
                         DeckButtonDialog (one button: what it runs + its values, label, colour, icon, page).
                         Data: core/deck/ (Deck → DeckPage → DeckButton; DeckStore = config/live_deck.json, made
                         from the flows until first saved; `version` lets open tabs redraw after a save)
  static/                served at /static: drawflow/ (vendored Drawflow 0.0.60, MIT), flow_boxes.js/.css
  services/              non-visual GUI helpers: RemoteLoginMiddleware (an ASGI gate for pages and NiceGUI's
                         socket: another device gets /login until signed in, and a socket only for a login page;
                         the API keeps its own tokens), OpenPages (every open page; AppShell attaches each one), confirm
                         dialog service and message service (both show on every open page), activity log, UI registry,
                         plugin context, page openers (window/browser)
devtools/tested/         `python -m streamer_toolbox.devtools.tested`: makes docs/tested/ (a row for everything, the
                         README's table; ticks and notes stay). It calls `assemble()` of `assembly/toolbox_assembly` (the toolbox put
                         together, not started) with an empty config in a throwaway folder. `checked <row> ...`
                         sets "AI checked" to today. `window` (docs/tested/test-window.bat / .sh) is the test window:
                         TestWindow, a small NiceGUI page of its own on port 8849 that only reads and writes
                         docs/tested (one file at a time in the menu's order, Back / Next, search, ticks, notes),
                         so it stays open next to the toolbox and through its restarts
devtools/package/        `python -m streamer_toolbox.devtools.package`: Packager (the archive of the toolbox: what
                         git tracks minus the developers' files, plus start scripts; only what is tested unless
                         `everything`) and DocBuilder (the docs as their own download: the manual, the files for AI)
devtools/box_gen/        class generator for developers: a service spec (JSON with example answers) → answer
                         dataclasses, actions class, fake, test (docs/PLAN_box_maker.md; never overwrites)
plugins/                 plugin loader, manifest (plugin.json), PluginSettings (the plugin interfaces are in
                         core/interfaces/). How to write one: docs/PLUGINS.md
```

`tests/` mirrors this folder by folder (`tests/core/actions/test_action_registry.py` tests
`core/actions/action_registry.py`; a test of one part of a class sits next to it, `test_flow_runner_switch.py`),
one class per file. Fakes are in `tests/fakes/`, builders in
`tests/helpers/`. SAMMI and Mix It Up are tested with `httpx.MockTransport`, OBS with
`FakeConnectableObsClient`; nothing talks to the real programs.

User files live in `config/` (gitignored except `toolbox.example.toml`): `toolbox.toml` (settings, one
`[table]` per connection, `[sound] folder`), `vts_token.txt`, `twitch_token.json`, `vts_positions.toml`,
`variables.json`, `flows/`, `flow_templates/`.

## Starting and restarting (2026-10-01)
- `python -m streamer_toolbox` (also start.bat / start-browser.bat) is the **launcher** (ToolboxLauncher): it runs
  the toolbox itself as a child (`--child`, stdin = a pipe), opens the page once the child answers, and starts the
  child again when it ends with exit code 3 (`RESTART_EXIT_CODE`). The app window belongs to the launcher, so it
  stays open over a restart and the page reconnects.
- Settings → Restart: ToolboxRestart.request() → app.shutdown → the child exits with 3.
- The window's X → launcher.stop() closes the child's stdin → ParentWatch (raw `os.read` on fd 0; a thread in
  sys.stdin's buffered reader crashes Python at shutdown) → app.shutdown. The launcher killed = same, so no
  toolbox is left running without its window.
- Processes on Windows: launcher = `.venv` stub + python, child = stub + python with `--child` in its command line.

## Adding a service (e.g. YouTube)

1. `connections/youtube_connection.py` with `class YoutubeConnection(ConnectionBase)`:
   - `id`, `title`, `icon`; `fields()` (what its tab asks for; `secret=True` for passwords/tokens);
   - `start()` / `stop()` / `test(settings)`: `test` returns a `ConnectionStatus` (it may ask the streamer once,
     like VTS pairing or the Twitch login; `start` never does);
   - `add_actions(actions)`: the actions it offers (named `youtube.*`, each with a `group`);
   - events: take the `EventBus` and `publish("youtube.<what>", {...})`; flows with a matching trigger start.
2. Everything it needs besides that class goes in `connections/youtube/`.
3. Add it to the list in `assembly/built_in_connections.py`, reading its `[youtube]` table from the config.
4. Tests in `tests/connections/test_youtube_connection.py`, services faked (httpx.MockTransport, a local
   websocket server like `tests/fakes/fake_eventsub_server.py`).

The Connections page gets a tab for it automatically. Settings are saved into its table in `toolbox.toml`
when **Connect** succeeds. `enabled` defaults to false: a connection is off until Connect or its switch, and
from then on it connects at every start until switched off.

## How a connection behaves

- Toolbox start: `ConnectionManager.start_all()` starts every enabled connection. A failure shows on its tab;
  it never stops the toolbox.
- **Connect** on the tab: tests what was typed (empty fields keep the saved value). Only on success: switch on,
  save, reconnect. A failed test changes nothing.
- On/off switch: saves `enabled` and connects or disconnects right away.
- Actions of a connection that is off raise `NotConnectedError`; if it's on but failed at start, an action tries
  again (e.g. OBS started after the toolbox) and the status updates.
- Every 5 s the manager calls `keep_alive()` on each switched-on connection (never during a GUI restart of that
  connection). `ConnectionBase.retry_when_down = True` (OBS, SAMMI, Mix It Up, VTS) runs `start()` again while in
  ERROR; OBS and VTS also notice a dropped socket and go to ERROR first. So a program started after the toolbox
  gets connected by itself (VTS with the saved token only, never the Allow popup).

## How a flow gets started (2026-10-01)

Custom triggers (2026-10-02, his round-18 idea: one flow for every platform): core/triggers. A CustomTrigger
(name, description, sources = FlowTriggers) lives in config/custom_triggers.json (CustomTriggerStore).
CustomTriggerRouter (EventBus) publishes a `custom` event when an event matches a source: the source event's
data + trigger, platform, source (its kind); a custom event never fires another one. CustomTriggerActions
adds `trigger.fire` (SAMMI / Kit / API / a flow box). Flows listen with FlowTrigger("custom", {"trigger": name});
renaming goes through FlowLibrary.rename_custom_trigger. Every Twitch event carries platform = "twitch".
GUI: Triggers page (sidebar), Redeems tab → Connect (new flow / existing flow / custom trigger).

Redeem triggers keep the reward's id (2026-10-02, his ask: SAMMI goes by name and breaks on a rename):
`reward = "Lizard", reward_id = "…"`. FlowTrigger matches by `reward_id` when it has one (ID_KEYS); a typed
name or pattern (`Lizard*`) has no id and matches by name. The name is kept current: FlowTriggerRouter calls
FlowLibrary.rename_reward on every redeem (title + id in the event) and on the `twitch.rewards` event that
TwitchConnection publishes once after connecting (the whole reward list). The trigger editor gets id → title
from TwitchConnection.reward_choices and shows the current name, or says the reward is gone. Pause reward /
Reward on / off keep the id too (older flows' names still work).

- Triggers: FlowTrigger.match = event fields (* wildcards, like SAMMI) plus two special keys: `words` (chat:
  one of the comma-separated words stands on its own in the message) and `who` (chat: the message's `role` is at
  least viewer / sub / vip / mod / broadcaster). The editor's chat trigger edits these via core/flows/chat_match.py
  (Command → `command`, Has word → `words`, Pattern → `message`).
- Twitch events: connections/twitch/eventsub_events.py lists the subscriptions (11; refused ones are skipped and
  shown as "Not available") and maps each notification to a toolbox event. Shared chat from the other channel
  is dropped (SAMMI's "only own chat"). VTS events: VtsConnection.EVENTS.
- FlowTriggerRouter starts every matching flow side by side. Before a start: QUIET kinds skip while running,
  FlowCooldowns (flow.cooldown, flow.user_cooldown by user_login) hold it back. Failed or held back + flow
  refund_on_fail + a redeem → the refund hook (TwitchConnection.finish_redeem, only toolbox-made rewards).
- FlowRunner.gate (FlowGate) applies flow.when_busy to every real run (trigger, button, API, flow as a box):
  alongside, queue (one asyncio.Lock per flow, in order) or skip (FlowSkipped). Test run ignores it.
- Stretchable wait (Wait box `if_started_again` = restart / add): before when_busy, `gate.stretch(flow)` pokes
  every run of that flow that hasn't got past such a wait (core/flows/retrigger.py); the new start doesn't
  run and gives `STRETCHED`. The run's Retrigger reaches the Wait box through the `current_retrigger`
  ContextVar (set in gate.enter). Test run: plain wait.

## Actions and the flow editor

`actions.add(name, handler, description, label, group=..., options=..., capture=..., ports=..., flow_only=...)`:
- category = the part before the dot (`obs`, `vts`, `logic`, ...; titles in `CATEGORY_TITLES`), `group` = the sub
  category in the editor's Add menu (Category → Sub category → Action, like SAMMI, with search).
- `options = {"param": async () -> list[str] | dict[str, str]}`: choices for that parameter (OBS scenes, VTS
  models/hotkeys); a dict is value → label (SAMMI buttons: ID → "text · deck [ID]").
- `capture`: the **Save current** button. `"other.action:param"` runs other.action and stores its result in the
  variable that `param` points at (vts.move_model_to → vts.get_model_position); `"other.action"` runs it with the
  box's matching parameters.
- `ports = ("then", "else")`: a box with several outputs; the handler returns True/False (or a port name), a
  list of port names (Repeat: fired one after the other) or an async generator of port names (For each: it sets
  its variable, then yields "each"; the runner finishes that round before asking for the next).
- `fills = {"request": provider}` (value → {other field: value}) fill other fields when a field is set, only
  where the other field is empty or still holds the last fill (RegisteredAction.filled; NodeEditor._set_param
  rebuilds the form); `live_hints = {"data": provider}` (box values → hint text). Used by the Raw request.
- Add trigger window (gui/components/flow_editor): trigger_kinds.py (TRIGGER_KINDS, TRIGGER_INFO = one line
  each, TRIGGER_CHOICES = a plugin trigger's dropdown) + TriggerCatalog (groups: Toolbox, Any platform, then
  the programs by name; search) + TriggerPicker (the same window shape as Add box). It gives a TriggerEntry.
- Add box window (gui/components/flow_editor): ActionCatalog (order: basics first, flows last; groups; search =
  every word anywhere) + ActionPicker (search on top, categories left / a row on a phone, boxes right). Show =
  one BoxFilter (round 21): the catalog is built with it, so categories, counts and search stay inside it; the
  one picked is kept in app.storage.general["box_filter"] (a filter that's gone = all boxes). The categories
  of connections that are switched off are left out (`switched_off` in `assembly/toolbox_assembly`), "Show them anyway" brings
  them back for that window.
- `files = {"file": MEDIA_TYPES}` (round 21): the field holds a file on this PC; ParamInput adds a folder button
  that opens FileDialog (lists through FileBrowser, so it also works from another device and gives the real
  path; `()` = any file, FOLDER = pick a folder; a typed name = a file that isn't there yet).
- `labels = {"lowest": "From"}`, `hints = {"seconds": "How long, e.g. 2 or 0.5"}`: a field's name and one help
  line in the box form; without a label the name shows as words ("if_started_again" → "If started again").
  Choices keep the order the options provider gives; lists longer than 12 (scenes, SAMMI buttons) go A-Z.
- Helpers on wires (core/data/value_helpers.py, his "data as a class" idea): a wire path part `@name` applies a
  helper to what's there: `${box.n3.@keys}`, `${box.n3.@kinds}` (key → kind), `@count`, `@kind`, `@first`,
  `@last`, `@text`; also in the middle (`${box.n3.items.@first.name}`). The field's "from box" list offers each
  dot's helpers right below it, only those that fit the dot's kind when it's known: one text, number or yes/no
  has none (round 21). A whole result's kind: "object" with declared outputs, else the handler's return type,
  else its last result (BoxDots.output_kind); Start fields are plain unless an input's default says more.
- `port_fields = "case"` (Switch): the box has any number of fields case_1, case_2, ... (count kept in `cases`,
  because empty fields aren't saved), each also an output before `ports`. Outputs are per box:
  `action.ports_for(node.params)` (core/actions/numbered_fields.py); everything that asks for a box's outputs
  passes its params. The form shows one field per case with × and "+ Add case"; taking one away renumbers the
  later cases and their wires (FlowDraft.remove_numbered), run through the `edit` hook of on_change so the box
  view reads back the canvas (old output names) first.
- `editors = {"animation": "vts_animation"}` (2026-10-01, his "custom variables in boxes" idea): a value the box
  keeps itself (any JSON-like object, stored in the flow file's params), edited in its own window instead of a
  ParamInput. EDITORS (value_editors.py) maps the kind to its field class (AnimationInput: map + one line + Edit opens
  AnimationDialog); the class's `text(value)` is the box line. The window can Save to file / Load from file:
  BoxValueFiles, `config/box_values/<kind>/<name>.json` (a copy, not a link). New kinds: an input class with
  build() + text(), one entry in EDITORS. The class also gets the box's params (PlacementInput: its scene).
- `obs_placement` (round 23): PlacementInput + PlacementDialog. The window runs obs.put_place_marker (a
  see-through colour source in the scene, at the place the box has), he drags / sizes it in OBS, Use this place
  runs obs.take_place_marker (reads its transform → ObsPlacement, removes it). Applying = position + bounds
  (SCALE_INNER) of that size, so any source is fitted into the marker's box.
- Model animation (connections/vtube_studio: VtsAnimation, VtsAnimationStep, VtsAnimationPlayer; ModelMover in
  core/interfaces): steps = spot + seconds + wait; fixed spots or changes from where the model starts
  (as_relative / as_fixed calculate the steps over from a base). VTS moves take 0..2 s, so a longer step goes
  as eased frames (30/s, seconds 0). Rotation changes go the short way (VtsPosition.minus / towards).
  One animation at a time (VtsConnection._animation): a new one cancels the one playing; the waiting box sees
  it end, not an error (asyncio.wait, not await). Loop forever runs in the background and the box returns at
  once; Stop model animation (vts.stop_animation) cancels it, optionally back to where it began
  (player.start / go_back). Stopping the connection stops it too.
- `entries = ("stop",)` (2026-10-02, the Loop box): extra run dots on the box's left after its normal one. A
  wire records which (`FlowWire.entry`, `entry = "stop"` in the flow file; empty = the normal dot); Flow.targets
  gives the normal ones, Flow.entries the others. Such a box runs once at a time per flow (a second start:
  "already running"); a wire reaching an entry in any run of the flow goes to the running box as a BoxSignals
  message (core/flows/box_signals.py; the runner sets BoxSignals.current() right before calling the box, so
  handlers keep plain parameters). On the canvas: input_1, then the entries (red, labelled), then the data dots;
  node.data.entries in flow_boxes.js / DrawflowGraph shifts the data dot numbers.
- Loop (logic.loop, ports each / stopped): an async generator like For each; between rounds it waits `pause`
  (at least 0.05 s) or until stop arrives; a stop ends it after the round that's running. Rounds of any
  generator don't add up toward MAX_RUNS; a run keeps its latest 1000 results. Test box: the first 20 ports.
- `flow_only=True`: not on Live, in the SAMMI deck or GET /actions (If, Wait).
- End box (logic.end, 2026-10-02): FlowRunner.register runs a flow used as a box in its own task and goes on
  when an End box is reached (FlowRun.ended) or the flow is done; the rest runs on (a failure there is logged).
  Named End boxes (Flow.ends) are the box's ports; its result then carries `_end` (END_KEY) = the one reached.
- `live=True`: a reading action without parameters (loaded model, current scene); a box field can use it as a
  **Live value**, `${get.vts.get_model}` or `${get.vts.get_model_position.x}`, run when the box runs.
- `data_outputs="fields"`: the box's data outputs are the fields listed in that parameter (`{name: kind}`, Split
  data) instead of the one "result" output.
- Every box can `save_as` its result in a variable; parameters can be `${var.name.field}`, `${input.x}`,
  `${event.x}`, `${box.n3.field}` (a value that is only a placeholder keeps its type, e.g. a position object).

Flow semantics: each wire from a port starts its target; several wires from one port run at the same time. A
box with two wires in runs twice (Wait for all joins them). A failing box stops its branch; the flow reports
the first failure. Connection tabs only hold connection settings.

Data wires (orange, round 11): a field whose source is "Wire from a box" is `${box}` until wired, then
`${box.n3}` (n3's result) or `${box.n3.x}` (one field; a Split box has one output dot per field). In the box
view it's a square dot on the left of the box; results are square dots on the right, after the run dots
(Drawflow: `input_1` = run in, `input_2..` = wired fields; outputs = ports, then data outputs; the dot names are
kept in each Drawflow node's `data` so reading back survives form edits). When the field is read: if n3 has run
wires into it, its latest result in this run is used (error if it hasn't run yet; Test box falls back to its
last result); if it has none, n3 runs right then, every time a box needs it, like a Live value (its outputs
don't fire). Actions with ports (If, Ask yes/no, For each) and `-> None` actions have no result dot.
Declared outputs (`outputs={"width": "number", ...}` on actions.add): the keys a result always has (Video
info, Get model position, Set source size). Since round 12 they are **not** dots of their own (his wish: one
"result" dot); fields still pick `${box.n3.width}` from their list, and it's drawn from the result dot. Every
box with fields has a **"by name"** dot first on the left (data_in `*`, BY_NAME): a result dropped there isn't
kept as a wire; flow_boxes.js sends tb_flow_by_name and WireMatcher.by_name sets each field named like one of
the result's keys (known: declared outputs / Split fields / Start fields; else a sample) to `${box.n3.<key>}`,
leaving fields that have a value or another wire. A Split box wired to a result with known keys takes them as
its fields at once (BoxDots.fields_from_wire); Find fields still reads a sample otherwise. A **Flow output** box (`logic.output`, name + value) makes a
flow used as a box give back {name: value} with a dot per output (Flow.outputs). Kinds: KindCheck (core/data)
gives a field's kind from its parameter type and warns when a wire brings the wrong one (text → number).
Flow.data_loop(): saving refuses orange wires that go round. Editor extras: **Wire by name** (WireMatcher +
WireByNameDialog: same-named outputs → fields), **Test run** (FlowRunner.test_run: results + first failure,
shown on each box), long orange wires as short tagged ends (flow_boxes.js tbFlowStubs, a view switch).
The Start box has an orange dot per flow input and per field its triggers give (EVENT_FIELDS): `${box.start.user}`
= the event's data merged with the flow's inputs; a field that isn't there (a button press, no event) is empty.

Triggers (`[[triggers]]` in a flow file): `twitch.redeem` (reward), `twitch.chat` (message, `*` = any text;
events also carry command and args), `timer` (every = seconds). Timer runs are quiet: a run still going is
skipped, and only failures reach the activity list.

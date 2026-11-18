# Settings changes

What changed in the settings folder (`config/` next to `toolbox.toml`), version by version. His rule
(2026-11-05): "make sure you write down the settings changes and write a version updater".

## How the version updater works

- The settings folder has a number: `settings_version` in `toolbox.toml`'s `[toolbox]` table (none = 0).
- Each change of the folder's shape is one **step** (a `SettingsUpgrade`, `core/upgrades/`). At start the toolbox
  runs every step newer than the folder's number, in order, once, and writes the new number after each one. The
  log says what each step changed ("settings upgrade 2 (Twitch accounts): ...").
- **Backup first** (his rule, 2026-11-05: "before a setting update, always backup the settings"): before the first
  waiting step runs, the settings folder goes into `backups/upgrades/settings-v<old>-before-v<new>-<date>_<time>.zip`
  (like the starter's backup: without `cache/`, `backups/`, `app_window/`). Kept: the **5 newest** and the
  **first of every day** ("just in case we have 5+ version updates in one day"); the starter's own clean-up never
  touches this folder; first-of-day ones older than 30 days go ("30 days is fine"). **No backup, no upgrade**: the settings stay as they are, a "Settings not upgraded"
  button shows next to the toolbox's name, the next start tries again. A new, empty settings folder gets no
  backup (nothing to keep). To go back: unpack the zip over the settings folder (with the toolbox closed).
- Flow exports carry the number they were made at. Importing an older one runs the steps' flow part on it; an
  export from a **newer** toolbox is refused ("update this toolbox first").
- Settings from a newer toolbox are read as they are, nothing is changed, and a yellow "Newer settings" button
  shows next to the toolbox's name.
- A new step: a `SettingsUpgrade` class with the next `version`, added to the list in `toolbox_assembly.py`,
  `SETTINGS_VERSION` raised by one (`core/upgrades/settings_version.py`), a test that starts from the old
  shape, and an entry below. Running a step twice must change nothing.

Small additions that an older toolbox simply ignores (a new key with a default, a new default event type) don't
need a step; they are listed under "Without a step" in their version's entry.


## After version 7, not released yet (no new number)

Without a step:
- `live_deck.json`: a button may have `confirm` (asks before it runs), `state` (the output of its flow it follows)
  and `on_label` / `on_color` / `on_icon` / `on_text_color` (its look while that output means on). Missing: false /
  empty. An older toolbox ignores them (the button just runs and looks the same).
- New file `live_states.json`: on / off of the flow outputs Live buttons follow (`{flow: {output: true}}`),
  so a button's state stays after a restart (his 11-18). Missing or broken: everything off.
- New folder `fonts/`: font files the toolbox hosts for every device (uploaded in Settings → Fonts, copied
  from this PC, or put there by hand). New file `fonts.json`: `{"this_machine": [names]}`, fonts of this PC
  used by name. Missing on Windows: the twelve fonts the font fields offered before. Older toolboxes ignore both;
  a text whose font is hosted shows another font there.
- Per browser (not in the settings folder): `live_start_page` (the page Live opens with on that device),
  `live_editing`, `live_clipboard`.

## Version 7 (2026-11-16)

Step: `ChatEmotesUpgrade` (`core/upgrades/chat_emotes_upgrade.py`). His "we don't need emotes and emoji_dict.
remove the old one".

| Before (version 6) | After (version 7) |
|---|---|
| the chat event type that came with the toolbox has `emotes` (Twitch's list of the message's emotes) | gone; `emoji_dict` has the emotes |
| a Send chat box with the field `emotes` | without it; a field that gave an emoji dictionary (`${box.….emoji_dict}`) moves to `emoji_dict` when that has none |

Without a step:
- Imported StreamElements chat widgets get their emotes (data.emotes, tags, renderedText) from `emoji_dict`: each
  whole word of the message in it; the id is Twitch's when the address is Twitch's, else the word.
- The flow "Twitch pfp and chat emotes" reads its inputs as wires from the Input box (`${box.input.…}`); one made
  before reads `${input.…}` (both work). "Add default flows" → "Update them" makes it new.
- An event list's event can be changed in place, and a new one's look copied from another (no new settings).
- The boxes Twitch emotes and BetterTTV emotes have a field `folder` (shared folder of the kept pictures; missing:
  `twitch_emotes` / `bttv_emotes`, empty: the box's own). Flows made before keep working; their pictures are
  downloaded once more into the shared folder.

## Version 6 (2026-11-16)

Step: `EmojiDictUpgrade` (`core/upgrades/emoji_dict_upgrade.py`). His emoji dictionary.

| Before (version 5) | After (version 6) |
|---|---|
| the chat event type that came with the toolbox | the values `picture` (v0.4.1 and before never got it) and `emoji_dict` at its end, those it hasn't (a type he made himself stays as it is) |
| v0.4.1's `Event: chat`, unchanged (the chat Start box straight into Send chat) | made new: `Event: chat` for every platform but Twitch, `Event: chat · Twitch` with the picture and the emotes |
| `Event: chat · Twitch` as step 5 made it from dev.5 to dev.7's chat flow (its Send without `emoji_dict`) | made new with `emoji_dict` |

Without a step:
- `Event: chat · Twitch` (made new by "Add default flows" → "Update them"): Start → the box "Twitch pfp and chat
  emotes" (a flow of its own, as a box: If user id → Remembered value / picture / keep → Choose value → Twitch
  emotes → End) → Send with `picture` and `emoji_dict`. Flows made before keep their shape.
- The box Twitch emotes (`twitch.emotes`, field `keep`): its kept pictures are in `cache/media/` like Keep media
  locally's. An older toolbox doesn't know the box.
- A list's text cell: `emoji_dict` (a value's name) and `emoji_size`; a list entry's `layers` (back, front). An
  older toolbox draws the text without pictures and the entry without layers.

## Version 5 (2026-11-15)

Step: `ProfilePictureUpgrade` (`core/upgrades/profile_picture_upgrade.py`). His round 90.

| Before (version 4) | After (version 5) |
|---|---|
| a flow's box `twitch.profile_picture` with `user` and `platform` | `user_id`; `platform` is gone (only Twitch; the platform check is an If on the flow). A flow whose box had a platform gets a log line: put an If before it |
| the chat flow dev.5 to dev.7 made (Start → picture → keep → Send), unchanged | split (his round 90): `Event: chat` (any platform) → Set variable `event_chat_platforms_with_own_flow` (Create if none) → List has platform → else → Send; and `Event: chat · Twitch` (Twitch chat) → Remembered value → found → Send, no value → picture → keep → Remembered value's `set` dot. `twitch` goes into the list. The main flow's name and on / off stay |
| `cache/twitch_pictures.json` (the picture box's own day cache) | deleted: the box asks Twitch each time, Remembered value keeps the address |

Without a step:
- `cache/remembered_values.json`: the values of the box Remembered value, by group ({group: {name: {value, at,
  used, keep}}}). An older toolbox doesn't read it. Deleting it only means asking again.
- Set variable's field `only_if_new` (Create if none; off when missing). An older toolbox refuses a Set
  variable that has it.
- Variables `event_<type>_platforms_with_own_flow` (a list of platform names): a toolbox-made main event flow
  leaves those platforms to their own flow. Made by the flow itself (Create if none) and by the toolbox
  when it makes a platform flow. Main flows made before keep their shape (they send every platform; only
  chat has a platform flow so far, and its old flow is made new above).
- The If box's field `ignore_case` (on when missing, as before). An older toolbox refuses an If that has it
  switched off.
- A box can have run dots that start it (`starts`); a flow wire into one carries its `entry` (`"set"`). An older
  toolbox doesn't know the box Remembered value at all.


## Version 4 (2026-11-06)

Step: `RumbleAccountsUpgrade` (`core/upgrades/rumble_accounts_upgrade.py`).

| Before (version 3) | After (version 4) |
|---|---|
| `secrets/rumble_address.txt`: the one Rumble address | `secrets/rumble/<name>.txt`: one file per account. The old file is moved to `rumble.txt`; Connect renames it after the channel / user name in Rumble's answer |
| no main account | `[rumble] main_account = "rumble"` |

Without a step: `[rumble] multiple_accounts`, `bot_accounts` (unused: read only), `listen`; Rumble events carry
`account` and `main_account`.
- `alerts.json`: a piece of kind `"picture"` with a `"file"` (his round 85: pictures and videos as pieces). An older
  toolbox leaves such a piece out (it only reads the kinds it knows); the alert's other pieces stay.
- `media/<export title>/`: the files an imported `.toolbox` export brought (pictures, sounds of its alerts and
  flows); the alerts and flows name them by their full path, like files picked by hand. Nothing reads the folder
  itself, so an older toolbox doesn't mind it. A `.toolbox` file carries the settings version it was made at
  (flows from an older one are upgraded on import; one from a newer toolbox is refused).
- `config/widgets/<name>/widget.js` of a widget saved in the widget editor (an Element's settings): the editor's
  own keys `toolbox` (on the settings: `top_first`; on a layer: `off`, `front`; on a piece: `react`, `goal`,
  `ticker`), the piece kinds `shape` and `goal`, the alert editor's animation names. An older toolbox draws such
  a widget without them (no shapes, goal bars or running tickers; fades instead of slides). Imported Elements
  are unchanged until they are saved in the editor.
- The same widget.js: the piece kind `eventList` with `toolbox.list` (his round 89: an event or chat history;
  `count`, `gap`, `newest`, `stays`, `keep`, `enter`, `enter_seconds`, `entries` with a `table` of
  cells each). An older toolbox doesn't draw it (the widget's other pieces stay). On the widget page it keeps
  the last entries in the widget's `data/store.json` under `toolbox-event-list:<piece name>`: data the widget
  gathered ("Remove all of it" on the widget page takes it away). A profile picture is no list setting: a flow
  gives it as an event value (his 11-13).
- `cache/twitch_pictures.json`: the profile picture addresses the box "Twitch profile picture" got from Twitch
  (at most 5000 people, a day each). Only that box reads it; deleting it only means asking Twitch again.
- The default event type `chat` has a value `picture` (his 11-14), and its own flow (made the first time something
  uses `chat`) goes Chat → Twitch profile picture (`user_id`, `platform`) → Send chat with `picture` from that box.
  Only for a chat type that comes in new: one already in `event_types.json` keeps its values, and a flow made
  before stays as it is ("only the default that will get added"). An older toolbox sends `picture` as one more
  value and has no `twitch.profile_picture` box.

- `cache/media/`: pictures and videos the box "Keep media locally" downloaded (his ideas of 11-14 and 11-15).
  The place is the address: `flows/box/<flow>/<box id>/` for a box in a flow (served at
  `/toolbox/media/flows/box/<flow>/<box id>/<file>`, `latest.png` = its newest), `shared/<folder>/` for a box
  with a Folder and for Live / the API (`shared/media/`), `boxes.json` = which box keeps in which shared folder.
  Files are `<code>_<name>.<ending>` (code from the address, name from the box's File name). Each folder has an
  `index.json` (each file's address, when it was fetched and last used, its size; the folder's limits; each
  box's newest). A box left out at Save flow, or a deleted flow, loses its own folder. Only the toolbox reads
  it; deleting it only means downloading again. The chat type's own flow (made new) keeps the profile picture:
  Chat → Twitch profile picture → Keep media locally (File name = `user_login`) → Send chat, `picture` =
  `/toolbox/media/flows/box/event_chat/n3/<file>`. The dev builds' `cache/media/<folder>/` and `/media/kept/`
  are gone without a step (never in a release); a left-over `cache/media/media/` can be deleted.

An older toolbox on version 4 settings: finds no Rumble address (it looks for `rumble_address.txt`).


## Version 3 (2026-11-06)

Step: `YouTubeAccountsUpgrade` (`core/upgrades/youtube_accounts_upgrade.py`). His ask: "the multi account option
should be possible for every streaming platform".

| Before (version 2) | After (version 3) |
|---|---|
| `secrets/youtube_token.json`: the one YouTube login | `secrets/youtube/<name>.json`: one file per account, named after the channel's handle (else its title) as letters, digits and `_`. The old file is moved there and removed |
| no main account | `[youtube] main_account = "<name>"`: the moved login |

Without a step:
- `[youtube] multiple_accounts`, `bot_accounts`, `listen`: the YouTube tab's account list (like Twitch's).
- YouTube events carry `account` (a dot) and `main_account`, like Twitch's.

An older toolbox on version 3 settings: finds no YouTube login (it looks for `youtube_token.json`).


## Version 2 (2026-11-05, after v0.3.1)

Step: `AccountsUpgrade` (`core/upgrades/accounts_upgrade.py`). Plan: `docs/PLAN_multi_accounts.md`.

| Before (version 1) | After (version 2) |
|---|---|
| `secrets/twitch_token.json`: the one Twitch login | `secrets/twitch/<login>.json`: one file per account, named after its Twitch login. The old file is moved there (encrypted as before when a toolbox login is set) and removed |
| no main account | `[twitch] main_account = "<login>"` in `toolbox.toml`: the moved login |
| event type `chat_deleted` hears `delete-message` | it also hears `delete-messages` (all of a chatter's messages); added only to the type that came with the toolbox |
| `[twitch] client_id`, `client_secret`, `redirect_url` (a Twitch app of his own) | gone: only the toolbox's own Twitch app logs in (his "we don't need a custom one anymore"). A login made with an own app asks for one Connect; the step's log line says so |

Flows don't change. Nothing to do for the streamer (no new Connect), unless his Twitch login came from an app
of his own.

Without a step:
- New default event types, added hidden the usual way (`defaults_added` in `event_types.json`):
  `community_gift`, `superchat`, `member`, `charity`, `merch`.
- `secrets/` sub folders are encrypted too when a toolbox login is set or changed.
- `[twitch] multiple_accounts` (false), `bot_accounts` ([]), `listen` ([]): the Twitch tab's account settings.
- A trigger's `accounts = "a, b"` (Twitch triggers, when several accounts listen) and a box's `account = "name"`
  (Twitch boxes): flows that use them do nothing different in an older toolbox (it ignores the key / the
  field), so they don't need a step.
- `[twitch] follower_check` and `[youtube] follower_check` ("60" seconds, "0" = off): the follower check (his
  failsafe of 2026-11-05). What it has seen is kept in `config/followers/<platform>_<account>.json`
  (`{"filled": true, "ids": [...]}`, the newest 5000); a missing file only means the next check fills it again.
- "Any platform" triggers start only for the main account's events unless they say `accounts = "all accounts"`
  (his answer to OPEN 123). Before, there was no second account whose events came in, so nothing changes for
  flows saved before.

An older toolbox (v0.3.1) on version 2 settings: shows "Newer settings", reads them as they are, but finds no
Twitch login (it looks for `twitch_token.json`), and refuses flow exports made at version 2.


## Version 1 (2026-11-01, round 78, in v0.3.0)

Step: `EventsUpgrade` (`core/event_types/events_upgrade.py`, the work in `EventConversion`).

- Widgets' own inputs (`widgets/<name>/inputs.json`) become event types (`event_types.json`, Overlay → Events)
  and the widget's `events.json`.
- Alerts get an event type (`AlertRule.event`); their own inputs go. The old file is kept as
  `alerts.before_round_79.json`.
- In flows, `alert.play.<id>` and `widget.send.<widget>.<input>` boxes become the event's Send box with
  "only to" that alert or widget. Imported older flows get the same change.


## Version 0 (before 2026-11-01)

No `settings_version` key. Older files were upgraded where they were read (alerts.json from before round 65,
flows from before round 55 / 63); that still happens and keeps working on files copied in by hand.

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

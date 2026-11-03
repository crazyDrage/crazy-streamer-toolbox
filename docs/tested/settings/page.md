# Settings

| What | Name in the code | AI checked | Works | Understandable | Usable | Last change | Note |
|---|---|---|---|---|---|---|---|
| Settings | `/settings` | 2026-10-08 | - | - | - | - |  |
| General | `/settings?show=general` | 2026-10-08 | - | - | - | - |  |
| Other devices | `/settings?show=devices` | 2026-10-08 | - | - | - | - |  |
| Login | `/settings?show=login` | - | - | - | - | - |  |
| Add box filters | `/settings?show=boxes` | 2026-10-08 | - | - | - | - |  |
| What you see | `/settings?show=seen` | 2026-10-10 | - | - | - | - |  |
| Viewer roles | `/settings?show=roles` | - | - | - | - | - |  |
| Event recording | `/settings?show=recording` | - | - | - | - | - |  |
| Settings version: older settings upgraded once at start (toolbox.toml `[toolbox] settings_version`) | `SettingsUpgrades` | 2026-11-01 | - | - | - | 2026-11-01 |  |
| Newer settings warning next to the toolbox name (press: what it means; phone: icon only) | `HeaderNotice` | 2026-11-01 | - | - | - | 2026-11-01 |  |
| Update: Settings → General (version, Look for updates once a day, Look now), "Update x.y.z" next to the name, its window | `UpdatePanel` | 2026-11-01 | - | - | - | 2026-11-01 | Download and install not tried with a real release yet |
| Update: Which versions (releases only by default, test versions only when picked) | `UpdatePanel which versions` | 2026-11-01 | - | - | - | 2026-11-01 | The backup before an update is only tested by the tests |
| Info pop-ups (toasts) let clicks through to what is underneath; only their own buttons take a click | `look.css .q-notification` | 2026-11-01 | - | - | - | 2026-11-01 | Since round 81 only where a page has no info bar, and for Show message |
| Info bar at the bottom of every page: the newest message instead of a pop-up; Debug button with a count of new lines | `InfoBar` | 2026-11-02 | - | - | - | 2026-11-02 |  |
| Debug panel on the right: every message, flow run and box error, search, Clear; the last 10 kept through a restart | `DebugList` | 2026-11-02 | - | - | - | 2026-11-02 |  |
| Debug pop-out window (the panel's ⧉ button, /debug) (not in the toolbox any more) | `/debug` | 2026-11-02 | - | - | - | 2026-11-02 |  |
| Own window, less memory (Edge's extras off, one page process; in start-settings) | `--open lean-window` | 2026-11-03 | - | - | - | 2026-11-03 | off screen, demo; ~240 MB instead of 280-370 |
| Start without a window (headless) | `start-headless.bat` | - | - | - | - | 2026-11-03 | the same as --open none |
| Starter window: how it opens, Start, Open / Restart / Stop, tray icon, "Back up now?" on close | `start-settings.bat` | 2026-11-03 | - | - | - | 2026-11-03 | demo, off screen; ~30 MB |
| Starter: back up the settings (once a day, Back up now; keeps 10 daily + 10 monthly) | `SettingsBackup` | 2026-11-03 | - | - | - | 2026-11-03 |  |

# 04 · A program doesn't connect, or connects badly

## The problem

The toolbox talks to OBS, VTube Studio, SAMMI, Mix It Up, Twitch, YouTube and more. When one of them isn't
connected, buttons and flows silently do nothing on stream.

## What he told me, and what was wrong

| When | His words | What was wrong |
|---|---|---|
| round 3, 09-28 | "OBS is not auto connected?" · "restart toolbox to use OBS connection? it should work just by clicking connect button" · "is the OBS password not saved?" | It only connected at start, a new setting needed a restart, and the password field looked empty after saving |
| round 13, 09-30 | "if I start VTS after the toolbox, it should try to connect automatically" | A program started after the toolbox was never connected |
| round 29, 10-04 | "youtube had an GUI error" | The Connect button broke on tabs with a number field (YouTube and Rumble) |
| round 41, 10-08 | T.I.T.S.: "it takes a bit longer to connect and gives an error, but connects" | By the name "localhost" every connect waited 2 s for nothing (2.09 s against 0.00 s by 127.0.0.1), and T.I.T.S. needs two |
| round 41, 10-08 | "We need to make it possible to reconnect twitch (permission update)" | While the saved login worked, Connect never asked Twitch again, so new permissions could never be added |

## What prevents it now

| What | How | Code |
|---|---|---|
| Connects by itself | at start, and every 5 s for a program that isn't there yet; again when it comes back | `core/connections/connection_manager.py` |
| No restart for a setting | Connect tests, saves and connects; a failed Connect saves nothing | each connection's tab |
| A saved password is shown as saved | "✓ Password saved" under the field (the password itself is never shown again) | |
| T.I.T.S. by 127.0.0.1 | also when the address field says localhost | `connections/tits_connection.py` |
| Twitch asks again when a permission is missing | Connect compares the saved login with everything the toolbox needs | Twitch connection |

## How to check it again

- Start the toolbox first, then the program: its tab must turn connected within a few seconds.
- Close the program while connected: the tab says so; start it again: connected again.
- Connection tests: `tests/connections/`.

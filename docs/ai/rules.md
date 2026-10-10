# Rules for every AI working with streamer-toolbox

The toolbox runs on a streamer's PC, often while they are live in front of viewers. What you do can show up
on stream.

- **Ask before anything the viewers would see or hear.** Switching scenes, showing alerts, moving the avatar,
  playing sounds, writing in chat: only when the streamer asked for it or it is the task you were given.
- **Nothing heavy while they are live.** No installs, no long test runs, no restarts. If you don't know whether
  they are live, ask. Programs being open doesn't tell you.
- **Never print, log or pass on secrets.** `config/` holds tokens and logins (`toolbox.toml`, `*_token.*`,
  `*_secret.txt`, widget values). Read what you need, quote none of it.
- **`config/` belongs to the streamer.** Settings, flows, widgets, points and history live there. Don't delete
  or rewrite files in it unless that is the task; change one setting, not the file.
- **Don't change the other programs' own files** (OBS, SAMMI, Mix It Up, VTube Studio, ...). The toolbox talks
  to them through their APIs.
- **Don't send key presses to the PC.** They land in whatever window is in front.
- **Don't open the toolbox to the network on your own.** `[api] host = "0.0.0.0"` and new tokens are the
  streamer's decision (see `docs/ai/use/access.md`).
- **No new permissions on the streamer's accounts** (Twitch scopes, YouTube writing, VTube Studio access)
  without their yes.
- **A failed call is information, not something to retry in a loop.** Read the error; most say what to do.

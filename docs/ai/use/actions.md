# Which action for what

`GET /actions` is the real list for this toolbox (see `docs/ai/use/api.md`). This file only tells you where
to look in it. A name is `<category>.<what>`; the category says who does the work.

## By what you want

| You want to | Look for | Notes |
|---|---|---|
| Run something the streamer built | `flow.<name>` | One action per flow. The flow's inputs are its parameters. This is the best door: the streamer decides in the dashboard what happens, you only start it. |
| Tell the toolbox a tip / donation came in | `tip.fire` | `user`, `amount` (above 0), optional `currency`, `message`, `source`. Flows with a Tip trigger start, the Tip alert shows, widgets get it. |
| Show an alert on stream | `alert.show`, `alert.clear` | Viewers see it. |
| Send an event to the widgets on stream | `widget.send_event` | |
| Tell the streamer something | `popup.message` | Shows on every open toolbox screen. Asking yes / no (`popup.ask`) only exists inside a flow. |
| Play a sound on the PC | `sound.play`, `sound.stop_all` | |
| Read or change the toolbox's variables | `var.*` | Flows read the same variables. |
| Viewer points | `points.*` | get, add, set, spend, give, top |
| What happened earlier (follows, subs, tips) | `history.summary`, `history.recent` | The toolbox's own record. |
| Control a program | `obs.*`, `vts.*` (VTube Studio), `sammi.*`, `mixitup.*`, `twitch.*`, `youtube.*`, `vnyan.*`, `warudo.*`, `veadotube.*`, `tits.*`, `streamerbot.*`, `firebot.*`, `lumia.*`, `voicemod.*`, `discord.*` | Only work while that connection is switched on and connected; otherwise the call answers 500 with the reason. |
| The streamer's heart rate | `heartrate.get` | 0 until Pulsoid or HypeRate told one. |
| Something a plugin added | `<plugin id>.*` | |

## Things to know before you call

- **A flow is the safe way to do several things.** If you need a scene switch, a sound and a chat message
  together, ask the streamer for a flow and call that, instead of sending three calls
  and handling the failures yourself.
- **Names inside the programs are the streamer's.** Scene names, model names, reward names differ per PC. Ask,
  or use an action that lists them (names starting with `get_` or `list_` in `GET /actions`).
- **You can't create or edit flows over the API.** They are made in the dashboard (Flows page).
- **Not available over the API at all:** If, Wait, Run program, Write text file and similar flow-only boxes.
- `tip.fire` returns at once; the flows it starts run on their own, and you don't learn
  whether they worked. `flow.<name>` runs that one flow and a failing box comes back to you as a 500.

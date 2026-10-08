# streamer-toolbox: user guide

> **AI agents should read `llms.txt` instead.**
>
> This software is made with the help of AI: the code is written with Claude Code.

streamer-toolbox is one program for the things a stream needs glued together: buttons that do something in
OBS, VTube Studio, SAMMI, Mix It Up or on Twitch, flows that run when a viewer follows, subscribes or redeems,
and alerts and widgets on stream. You build everything by clicking; no code.

It runs on your own PC (Windows, 64 bit) and shows its pages in a window or in your browser. Nothing is sent
to a server of ours: there is none.

## Start it

1. Unpack the archive anywhere you like (for example `Documents\streamer-toolbox`). Not inside `Program Files`:
   the toolbox writes its settings into its own folder.
2. Double-click **Start streamer-toolbox.bat**.
   - The toolbox opens in its own window. Closing that window stops the toolbox.
   - **Start in the browser.bat** opens it as a browser tab instead and keeps running when the tab is closed
     (close the black console window to stop it).
3. The first time, Windows may show "Windows protected your PC" for the .bat file: *More info* → *Run anyway*.

Nothing is installed. Python and every library the toolbox needs are in the `python` folder of the archive.
To remove the toolbox, delete its folder.

### On Linux

The same archive starts on Linux. **This is new and has not been tried on a real Linux PC yet.**

1. You need `python3`, version 3.11 or newer, with `venv` (on Debian / Ubuntu: `sudo apt install python3-venv`).
2. Unpack the archive, then run `./start-linux.sh` in its folder (`./start-linux-browser.sh` for a browser tab).
3. The first start gets the libraries from the internet into a `.venv` folder inside the toolbox's folder.
   Nothing is installed outside it.

What differs on Linux: the toolbox's own window needs a Chromium browser (Chromium, Chrome, Edge or Brave),
otherwise it opens as a browser tab. Keyboard triggers need X11; under Wayland they may not see your keys.
Programs that only exist for Windows (SAMMI, Mix It Up) are not there on a Linux PC, so their connections
stay off.

### Your data stays in the folder

Everything the toolbox keeps is inside its own folder, nothing in Windows' user folders or the registry:

| Where | What |
|---|---|
| `config\toolbox.toml` | the settings |
| `config\flows`, `config\widgets`, `config\alerts.json`, ... | what you built |
| `config\history`, `config\points` | the record of follows / subs / cheers, and the viewers' points |
| `config\*_token.*`, `config\*_secret.txt`, `config\*_address.txt` | your logins. **Never share these files.** |
| `.nicegui` | small page settings (which tab was open) |

So the toolbox is portable: move or copy the whole folder to another place or PC and start it there. A
backup is a copy of the `config` folder. To send the toolbox to someone, send the archive you got, not your
own folder (yours holds your logins).

The address is `http://127.0.0.1:8850`. Another port: `Start streamer-toolbox.bat --port 8851`.

## The pages

The menu is on the left (on a phone: tabs at the bottom). An area with an arrow has a list below it. **Show
all** at the bottom of the menu gives every item an eye: click it to hide what you don't use.

| Page | What it is for |
|---|---|
| **Live** | Your button deck: big buttons that run a flow. The pencil switches to edit mode (buttons, pages, colours). |
| **Flows** | What the toolbox does: boxes connected by wires, started by a trigger (a redeem, a follow, a key, a timer, a button). |
| **Triggers** | Your own named triggers that several flows can listen to. |
| **Variables** | Values the flows remember (counters, texts, lists). |
| **Overlay** | What shows on stream through a Browser source in OBS: **Alerts** and **Widgets**. |
| **Tools** | Extra tools: your Twitch channel point rewards, **Points** (your own currency), and one per plugin (SAMMI decks as buttons). |
| **Connections** | One entry per program or service. Fill it in, press **Connect**. |
| **Plugins** | Which plugins are loaded. |
| **Settings** | Theme, restart, opening the toolbox from other devices. |

## First steps

### 1. Connect your programs

**Connections** lists them. Each one is optional and starts switched off: the toolbox talks to a program only
after you pressed Connect (or switched it on) on its tab. From then on it connects every time the toolbox starts.

- **OBS**: in OBS, *Tools → WebSocket Server Settings*, enable it, copy the password. Enter both in the
  toolbox and press Connect.
- **VTube Studio**: enable the API in VTube Studio's settings, press Connect, allow the plugin in VTube Studio.
- **Twitch**: press Connect and confirm the code on Twitch's page. An app of your own is optional: on
  `dev.twitch.tv/console` register one with the redirect URL `http://localhost:17563` and put its Client ID
  and Secret on the tab.
- **SAMMI**, **Mix It Up**: enable their local API, enter the address, Connect.
- **StreamElements**, **Streamlabs**: paste the token from their dashboard (the connection's tab has the link).
- **YouTube**: needs a Google Cloud project of your own (the tab says how), then Client ID, Client Secret,
  Connect. While you are live, chat messages, Super Chats, Super Stickers and memberships start flows.
  Writing in chat is off until you set "May write in chat" to yes (Google's permission for it is a big one).
- **StreamSocket Events** (a Twitch extension where viewers press buttons, for bits or free): put the secret
  from the extension's configuration page into `config/streamsocket_secret.txt` and switch it on. Each
  redeemed event starts flows with the trigger "StreamSocket event".
- **VNyan**, **Warudo** (3D avatar programs): switch the connection on. What happens is built in the
  program itself: a node with a name (VNyan: a "WebSocket" node, with Settings → Misc → WebSockets →
  Start Receiver on; Warudo: an "On WebSocket Action" node). A flow's "Send message to VNyan" / "Send
  action to Warudo" box with the same name runs it.
- **veadotube mini** (PNG avatar program): switch the connection on; the running program is found by
  itself. Boxes switch the avatar's state (picked from a list) or show one for a few seconds, and the
  trigger "veadotube state changed" starts a flow.
- **T.I.T.S.** (Twitch Integrated Throwing System): switch its API on in its settings, then the
  connection. Boxes throw an item or activate a trigger (picked from a list); a hit on the model and a
  trigger starting or ending start flows.
- **Streamer.bot**: start its WebSocket server (Servers/Clients → WebSocket Server), then the connection.
  "Run Streamer.bot action" runs an action you made there, picked from a list. Its events start flows
  with the trigger "Streamer.bot event" (by default Kick, Custom and General; the tab says which). If
  its server asks for a password, put it into `config/streamerbot_password.txt`.
- **Firebot**: switch the connection on. "Run Firebot effect list" runs a preset effect list you made
  there; its custom variables and counters can be read and set.
- **Lumia Stream**: put the token from its API settings into `config/lumia_token.txt`. Boxes run its
  commands and alerts and set the lights; the trigger "Lumia event" starts flows.
- **Voicemod**: ask Voicemod for an API key (the tab has the link) and put it into
  `config/voicemod_key.txt`. Boxes switch the voice, play a soundboard sound, flip its switches.
- **Pulsoid**, **HypeRate** (heart rate): put the token / key into `config/pulsoid_token.txt` /
  `config/hyperate_key.txt` (HypeRate also wants your id on the tab). The trigger "Heart rate changed"
  starts flows, and "Get heart rate" reads it.
- **Discord**: make a webhook for a channel (channel settings → Integrations → Webhooks) and put its
  address into `config/discord_webhook.txt`. "Post to Discord" writes there; names in the text only ping
  when the box says so.
- **Tiltify** (charity): needs a Tiltify application of your own (the tab has the link): its Client ID on
  the tab, its secret in `config/tiltify_secret.txt`, plus the user and campaign from the campaign's
  address. Each new donation starts flows with the trigger "Tiltify donation". It is not counted as a tip.
- **Crowd Control**: type your Crowd Control id (it starts with `ccuid-`) on the tab. Each effect a
  viewer asks for in your game starts flows with the trigger "Crowd Control effect".
- **Rumble**: put your Live Stream API address into `config/rumble_address.txt` (the tab has the link to
  Rumble's page). Chat, follows, subs, gifted subs and rants then start flows; Rumble can only be read.
  The toolbox only listens to their events (tips and co.).

Boxes of a program that is switched off are hidden when you add a box to a flow.

### 2. Make a flow

**Flows → New flow.** A flow starts at its Start box. **Add box** lists everything the connected programs
can do (switch a scene, play a sound, move the model, write in chat, wait, if / else, loops, variables, ...).
Drag from a box's output to the next box's input. A value of one box can be wired into a field of another.

Pick what starts it in the Start box (a channel point reward, a follow, a key, a timer, a custom trigger), or
leave it without a trigger and put it on a button on the **Live** page. **Test run** tries it at once.

### 3. Alerts

**Overlay → Alerts.** Press **Add it to OBS** once (or add a Browser source by hand with the address shown).
Each kind of alert (follow, sub, resub, gift subs, cheer, raid, tip) has a switch, a **Test** button and
**Settings**: text, picture / gif / video, sound, how long, where on the screen, how it comes in. In the
preview you drag the alert, drag the corner handle to resize the picture, and drag words onto the picture.

### 4. Widgets

**Overlay → Widgets** runs widget code made for StreamElements and imports your StreamElements overlays and
Elements, so they keep working without StreamElements. See `docs/WIDGETS.md`.

## Backup, moving, sharing

Everything you set up is in the `config` folder inside the toolbox's folder: `toolbox.toml` (settings),
`flows/`, `alerts.json`, `widgets/`, your logins and tokens. Plain files.

- **Backup**: copy the `config` folder.
- **Move to a new version**: unpack the new archive and copy your old `config` folder into it.
- **Never share the `config` folder**: it holds your tokens.

## Other devices (phone, tablet)

**Settings → Other devices**: set a password and switch it on, restart, then open the address shown there on
the other device. Windows asks once whether Python may use the network: choose *Private networks*. It is meant
for your home network only (the password travels unencrypted).

## For other programs

The toolbox has an HTTP API: `POST /action/<name>` runs any action, `GET /actions` lists them. Who may call
what is set under `[callers.<name>]` in `config/toolbox.toml` (see `config/toolbox.example.toml`). SAMMI can
get a ready-made deck with one button per action from **Connections → SAMMI**.

Plugins add boxes, tools and pages: `docs/PLUGINS.md`. AI agents start at `llms.txt`.

## License

Apache License 2.0 (`LICENSE`). You may use, change and pass on the toolbox. If you pass it on or build
something from its code, keep the `NOTICE` file with it, so people can see where it came from.

## When something doesn't work

- **The window doesn't open**: start **Start in the browser.bat** and read what the black console window says.
- **"Address already in use"**: the toolbox is already running, or another program uses port 8850. Start with
  `--port 8851`.
- **A connection stays red**: its tab under Connections says why (wrong password, program not running, API
  not enabled there).
- **An alert or widget doesn't show in OBS**: the Overlay page says whether OBS is showing the Browser source.
  In the source's properties, *Refresh cache of current page*.
- **After changing `toolbox.toml` by hand**: Settings → Restart.

## One trigger for every platform

Next to each platform's own triggers ("Follow" = Twitch, "Rumble follow", ...) there are the ones marked
**(any platform)**: chat message, follow, sub, resub, gift subs, cheer, raid, redeem, stream online / offline.
They start for every platform you connected; the Start box's `platform` says which one it was. Alerts and
widgets work this way by themselves: a Rumble follow shows your Follow alert.

## Points (your own currency)

**Tools → Points**. Viewers who write in chat get points every few minutes; a follow, sub, raid or cheer gives
a bonus. Switch **Give out points** on, set the numbers, give the currency a name, Save. A chat command
(`!points` at the start) tells a viewer how many they have.

In flows, the **Points** boxes do the rest: *Add points*, *Spend points* (gives `ok`: put an **If** on it for a
command that costs points), *Get points*, *Give points to a viewer*, *Top points*. Wire the Start box's
`user_login` into `viewer`.

Points are per platform (a name on Twitch and the same name on YouTube are two viewers). On Twitch, viewers
who only watch earn too (**Lurkers earn too**); that needs the Twitch login's "who is in chat" permission:
press Connect once on Connections → Twitch if the page says so. Names under **Never earn** (chat bots)
get nothing, and neither do you unless you switch **I earn points too** on.

**Mix It Up**: if your points live there, pick **Use Mix It Up's points** under "Where the points live": the
boxes and the chat command then work on Mix It Up's currency, and Mix It Up keeps giving them out. Or press
**Move the amounts over from Mix It Up** to copy everyone's amount into the toolbox once.

## History (what happened on your channel)

The toolbox writes down every follow, sub, cheer, raid and tip with its date (`config\history`). From that it
knows how many there were this stream, this week, this month and in all, and who gave most. Widgets get these
numbers by themselves; flows use the **History** boxes (*Get sums*, *Get recent*).

It only knows what happened while it was running. What was before can be brought over once from
StreamElements: **Overlay → Widgets → Latest names from StreamElements**.

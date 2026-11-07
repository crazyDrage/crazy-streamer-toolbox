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
2. Double-click **crazy-streamer-toolbox.exe**.
   - The toolbox opens in its own window. Closing that window stops the toolbox.
   - No `.exe` in your archive? **Start streamer-toolbox.bat** does the same, with a black console window
     next to it.
   - **Start settings.bat**: a small window to start it with. Pick how it opens (own window, own window
     with less memory, browser tab, no window), start, restart or stop it, and back up your settings: once a
     day when it starts, with "Back up now", and it asks "Back up now?" when you close it. It keeps 10 daily
     and 10 monthly backups (you can change both) in the `backups` folder of your settings. It has an icon
     next to the clock; tick "Start like this next time without asking" and it starts right into it.
   - **Start without a window.bat**: no window at all. Open `http://127.0.0.1:8850` in any browser or on your
     phone; close the black console window to stop it.
3. The first time, Windows may show "Windows protected your PC": *More info* → *Run anyway*. The program is
   not signed yet; that is all the warning means.

If it does not start, the file `start.log` next to the program says why (the `.exe` writes there what the
toolbox prints).

Nothing is installed. Python and every library the toolbox needs are in the `python` folder of the archive.
To remove the toolbox, delete its folder.

### On Linux

**The Linux download** (`crazy-streamer-toolbox-linux.tar.gz`) has its own Python and every library, like
the Windows one: unpack it (`tar -xzf ...`) and run `./start-linux.sh` in its folder
(`./start-linux-settings.sh` for the small start window, `./start-linux-headless.sh` without a window).
Nothing is installed and no internet is needed.
**This is new: it was started on Linux without a screen (the pages answer), but not yet used on a real
Linux desktop.**

An archive made for both systems at once (it has a `python` folder for Windows and `.bat` files) starts on
Linux too, but uses your PC's Python:

1. You need `python3`, version 3.12 or newer, with `venv`, and a C compiler (one library for the keyboard
   triggers is built on your PC). On Debian / Ubuntu: `sudo apt install python3-venv python3-dev gcc`.
2. Unpack the archive, then run `./start-linux.sh` in its folder (`./start-linux-settings.sh` for the small
   start window; it needs tkinter: `sudo apt install python3-tk`).
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
| **Live** | Your button deck: buttons that run a flow, on pages. The pencil switches to edit mode: drag a button to where you want it, drag its corner to change its size, click it to change what it runs, its colour, text colour, icon or picture. Each page has its own number of columns and rows and its own background colour. |
| **Flows** | What the toolbox does: boxes connected by wires, started by a trigger (a redeem, a follow, a key, a timer, a button). |
| **Variables** | Values the flows remember (counters, texts, lists). |
| **Overlay** | What shows on stream through a Browser source in OBS: **Alerts** and **Widgets**. |
| **Tools** | Extra tools: your Twitch channel point rewards, **Points** (your own currency), and one per plugin (SAMMI decks as buttons). |
| **Connections** | One entry per program or service. Fill it in, press **Connect**. |
| **Plugins** | Which plugins are loaded. |
| **Learn** | How the toolbox works, step by step, and examples: **Add to my flows** copies one into the folder Examples (switched off). |
| **Settings** | Theme, restart, opening the toolbox from other devices. |

## First steps

### 1. Connect your programs

**Connections** lists them. Each one is optional and starts switched off: the toolbox talks to a program only
after you pressed Connect (or switched it on) on its tab. From then on it connects every time the toolbox starts.

- **OBS**: in OBS, *Tools → WebSocket Server Settings*, enable it, copy the password. Enter both in the
  toolbox and press Connect.
- **VTube Studio**: enable the API in VTube Studio's settings, press Connect, allow the plugin in VTube Studio.
- **Twitch**: press Connect and confirm the code on Twitch's page. Nothing to set up: the toolbox logs in
  with its own Twitch app.
- **SAMMI**, **Mix It Up**: enable their local API, enter the address, Connect.
- **Several accounts** (Twitch, YouTube, Rumble): each tab has an account list: **Add account**, the **Main
  account** (used wherever no account is picked), **Remove**, and per account **Listen to its channel**. Switch
  on **Multiple accounts** and boxes and triggers of that platform get an Account field. A **bot account**
  (Twitch, YouTube) writes in your main channel's chat.
- **Missed follows**: Twitch and YouTube check your newest followers every 60 seconds (`Check for new followers
  every`, 0 = off); one Twitch missed still starts your follow flows, and nobody is thanked twice.
- **StreamElements**, **Streamlabs**: paste the token from their dashboard (the connection's tab has the link).
- **YouTube**: needs a Google Cloud project of your own (the tab says how), then Client ID, Client Secret,
  Connect. While you are live, chat messages, Super Chats, Super Stickers and memberships start flows.
  Writing in chat is off until you set "May write in chat" to yes (Google's permission for it is a big one).
  New subscribers come from the subscriber check (every 60 seconds, 1 quota point each time).
- **StreamSocket Events** (a Twitch extension where viewers press buttons, for bits or free): put the secret
  from the extension's configuration page into `config/secrets/streamsocket_secret.txt` and switch it on. Each
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
  its server asks for a password, put it into `config/secrets/streamerbot_password.txt`.
- **Firebot**: switch the connection on. "Run Firebot effect list" runs a preset effect list you made
  there; its custom variables and counters can be read and set.
- **Lumia Stream**: put the token from its API settings into `config/secrets/lumia_token.txt`. Boxes run its
  commands and alerts and set the lights; the trigger "Lumia event" starts flows.
- **Voicemod**: ask Voicemod for an API key (the tab has the link) and put it into
  `config/secrets/voicemod_key.txt`. Boxes switch the voice, play a soundboard sound, flip its switches.
- **Pulsoid**, **HypeRate** (heart rate): put the token / key into the field on its tab (HypeRate also wants
  your id there). The trigger "Heart rate changed" starts flows: at any change, at every change higher than /
  lower than / equal to a number, or once when it rises above / falls below one. "Get heart rate" reads it.
- **Discord**: make a webhook for a channel (channel settings → Integrations → Webhooks) and put its
  address into `config/secrets/discord_webhook.txt`. "Post to Discord" writes there; names in the text only ping
  when the box says so.
- **Tiltify** (charity): needs a Tiltify application of your own (the tab has the link): its Client ID on
  the tab, its secret in `config/secrets/tiltify_secret.txt`, plus the user and campaign from the campaign's
  address. Each new donation starts flows with the trigger "Tiltify donation". It is not counted as a tip.
- **Crowd Control**: type your Crowd Control id (it starts with `ccuid-`) on the tab. Each effect a
  viewer asks for in your game starts flows with the trigger "Crowd Control effect".
- **Rumble**: Add account on the tab and paste your Live Stream API address (the tab has the link to Rumble's
  page); more accounts the same way. Chat, follows, subs, gifted subs and rants then start flows; Rumble can only
  be read.
- **Fansly**: paste your chat's address on the tab (Fansly → Streaming → the 3 dots next to the chat → Copy
  Chat Url). No login: the toolbox reads the chatroom like a viewer. Chat messages, tips (also as the Tip
  trigger) and new subs then start flows; nothing is sent to Fansly. Fansly has no official API, so this uses
  their website's chat connection and can stop working when Fansly changes it.
  The toolbox only listens to their events (tips and co.).

Boxes of a program that is switched off are hidden when you add a box to a flow.

### 2. Make a flow

**Flows → New flow.** A new flow has a Start box wired to an End box; your boxes go in between. **Add box**
lists everything the connected programs can do (switch a scene, play a sound, move the model, write in chat,
wait, if / else, loops, variables, ...). Drag from a box's output to the next box's input. A value of one box
can be wired into a field of another.

**Ready-made flows:** Connections → Twitch (YouTube, ...) → **Add default flows** puts a few into a folder
of their own ("Twitch - default", each flow named "Twitch - default - thank a follow", ...); a window lets you pick which ones, switched off; **Learn** has examples to copy. Change the words, then switch them on.

**Start** is the flow's button (Live page, SAMMI, Kit, the API, another flow). **Add trigger** gives it one more
way to start (a channel point reward, a follow, a key, a timer, ...): each trigger is a Start box of its own,
wired like Start, and its orange dots are what happened (who redeemed, what they typed). A box reading those dots
gets nothing when another Start box started the run. The **Input** box holds the values a button or another
flow gives the flow. **Test run** tries it at once, from the Start box you pick.

Many flows? A flow's ⋮ menu (or its switch in the editor) and a folder's buttons have **Hide in list**: it is
left out of the Flows page and its side list, and still runs. **Hidden (n)** at the top lists them again; a
search always finds them. The folder **Alerts** (the flows that play your alerts) starts hidden.
A folder's **Switch folder off** stops all its flows at once (buttons, triggers, SAMMI, the API, other flows);
each flow keeps its own switch for when the folder is on again.

#### Run wires and value wires

A flow has two kinds of wires:

| | Run wire (round dots, solid line: teal; after an If green / red) | Value wire (square dots, orange dotted line) |
|---|---|---|
| What it says | "when this box is done, do that box next" | "this field takes that box's value" |
| Decides | **when** a box runs, and in which order | **what** a field gets |

What a box gives when a field reads it:

- **The box has a run wire into it**: it runs once, when the run wire reaches it. Every field that reads it
  gets that same value. A field that reads it **before** the run wire reached it gets an error ("box n3 hasn't
  run yet"): wire it to run earlier. Test run is kinder: there it gets the value the box gave last time.
- **The box has no run wire into it**: it runs **at the moment** a field reads it, once **for each** field that
  reads it. Its own outputs (then / else, done) don't go on to other boxes.
- **Boxes without run dots** (Value, Calculate, Get variable, Build text, Replace in text, ...): always the
  second way. They only work out a value, so reading them late or twice changes nothing.

**You ran a box, then took its run wire away:** nothing is kept from that run. From the next run on, the box
runs whenever a field reads it (the second way). For a box that asks a program (OBS, VTube Studio, ...) that
means it asks at that moment, once per field: "Get current scene → Switch scene → switch back" would read the
scene after the switch. Keep the run wire on a box whose value must be from one moment, or that does
something (plays a sound, moves the model): without a run wire it only runs when a field needs its value.

**The last value you see on a box** (its panel, its dots) is only a preview: kept in memory until the toolbox
stops, never used by a real run. A run reads the box again (with a run wire: when the wire reaches it; without:
when a field reads it). To keep a value, e.g. the model's position to put it back later, use "Save it in a
variable" on the box (or Set variable): a variable is kept in a file, also over a restart.

**Freeze a box** (its panel → Freeze): it runs once and keeps that answer, in the flow's file. From then on it
gives that answer and doesn't run in the flow: no run wire, no inputs (they're kept, hidden), its dots show the
saved values. **Run again** asks again and keeps the new answer; **Unfreeze** makes it a normal box with its
wires again. Good for something you look up once: your model's position, a scene's size, a list of items.
Deleting the box deletes its saved values. Boxes that give no answer (Move model, Play sound) or steer the flow
(If, Loop) can't be frozen.

### 3. Alerts

**Overlay → Alerts.** Press **Add it to OBS** once (or add a Browser source by hand with the address shown).
The list starts with Follow, Sub, Resub, Gift subs, Cheer, Raid and Tip. **New alert** adds your own (a name,
and the event it plays on). Each alert has a switch, a **Test** button and **Settings**: its name, its
**event** (its values are what it gets each time: the viewer's name, an amount, their message, a picture or a
sound; `{name}` in its words; an example for each), text, picture / gif / video, sound, how long, where on the screen, how it comes in. In the preview you
drag the alert, drag the corner handle to resize the picture, and drag words onto the picture.

An alert plays on an **event** (Overlay → Events: follow, sub, cheer, ... or one you make). The event's flow in
the folder **Events** ("Event: follow", ...) sends it on every follow, sub, ... to every alert and widget that
uses it; change it like any flow. A gifted sub plays no Sub alert: the gifter gets one ("Kit gifted 5 subs!").
A sound value makes a soundboard: one alert, a different sound from each button or redeem.

### 4. Widgets

**Overlay → Widgets** runs widget code made for StreamElements and imports your StreamElements overlays and
Elements, so they keep working without StreamElements. See `docs/WIDGETS.md`.

## Backup, moving, sharing

Everything you set up is in the `config` folder inside the toolbox's folder: `toolbox.toml` (settings),
`flows/`, `alerts.json`, `widgets/`, your logins and tokens. Plain files.

- **Backup**: copy the `config` folder.
- **Move to a new version**: when one is out, a button "Update x.y.z" shows next to the toolbox's name. Press
  it, read what's new, then **Download and install**: the toolbox stops, a small window with a moving bar shows
  while the new version goes in (don't start the toolbox yourself then), and it starts again by itself with
  "Updated to x.y.z" next to its name. Your `config` folder stays as it is. Settings → General: "Look for
  updates by itself" (at every start and every 6 hours) and "Look now". By hand still works: unpack the new archive and copy your old `config` folder into it.
- **Before every update** a copy of your settings goes into `config/backups/` (a zip, named with the version
  and the date). To go back: unpack it over the `config` folder.
- **Test versions** (`0.5.0-dev.1`, `-alpha.1`, `-beta.1`, `-rc.1`, before `0.5.0`): only offered when you pick
  them in Settings → General → "Which versions". They can break things.
- **Never share the `config` folder**: it holds your tokens.

## Other devices (phone, tablet)

**Settings → Other devices**: set a password and switch it on, restart, then open the address shown there on
the other device. Windows asks once whether Python may use the network: choose *Private networks*. It is meant
for your home network only (the password travels unencrypted).

## Login (a password for the toolbox itself)

**Settings → Login**: off by default. Without a login the toolbox starts by itself and connects to
everything. With one, your tokens, keys and saved logins (the folder `secrets` in your settings folder,
nothing else) are encrypted on your PC, and the toolbox asks for the password at every start: until you
typed it, nothing starts and nothing is connected. Switch it off again in the same place, with the
password. A forgotten password can't be recovered: delete the folder `secrets`, then type your tokens in
again and connect Twitch and YouTube again. It is not the password for other devices; that one stays its
own.

## For other programs

The toolbox has an HTTP API: `POST /action/<name>` runs any action, `GET /actions` lists them. Who may call
what is set under `[callers.<name>]` in `config/toolbox.toml` (see `config/toolbox.example.toml`). SAMMI can
get a ready-made deck with one button per action from **Connections → SAMMI**.

Plugins add boxes, tools and pages: `docs/PLUGINS.md`. AI agents start at `llms.txt`.

## License

Apache License 2.0 (`LICENSE`). You may use, change and pass on the toolbox. If you pass it on or build
something from its code, keep the `NOTICE` file with it, so people can see where it came from.

## When something doesn't work

- **The window doesn't open**: start **Start without a window.bat**, open `http://127.0.0.1:8850` in your
  browser and read what the black console window says. With **Start settings.bat**: the file
  `config/cache/starter.log` says it.
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
widgets work this way too: a Rumble follow plays your Follow alert (its flow starts on "Follow (any
platform)").

One flow for several events (a Twitch redeem and a Rumble chat command): give it a trigger for each. Each
one is its own Start box; wire them into the same boxes.

## Sub, Resub and Gift subs: which one starts when

| Trigger | Starts when | `user` is | Worth reading |
|---|---|---|---|
| **Sub** | someone gets a new sub: paid by themselves, or gifted to them | the new subscriber | `gift` (yes = it was gifted to them), `tier` |
| **Resub** | someone shares another month in chat | the subscriber | `months`, `message`, `tier` |
| **Gift subs** | someone gives subs away | the giver (empty when anonymous) | `amount` (how many), `tier`, `anonymous` |

When a viewer gifts 5 subs, **Gift subs** starts once (the giver, `amount` = 5) and **Sub** starts five times
(one per receiver, each with `gift` = yes). A flow on Sub that should only run for people who paid themselves
checks `gift` with an If box; the "Alert: Sub" flow's trigger already leaves gifted ones out (gift = false).

Hard to make happen for a test? The last real one of every trigger is kept as a file in
`cache\last_triggers\` in your settings folder, and a flow's **Test run** starts with its values.

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

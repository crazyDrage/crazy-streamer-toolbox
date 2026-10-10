# Custom widgets (StreamElements' format)

The toolbox can run custom widget code made for StreamElements: the four parts people share (HTML, CSS, JS,
FIELDS). Each widget becomes its own overlay page that you add to OBS as a Browser source. Nothing goes through
StreamElements; the events come from the toolbox's own Twitch connection.

Where: **Overlay → Widgets**.

## Using one

1. Get it in. Either **Import from StreamElements**: pick one of your overlays from the list (or paste its
   address from their overlay editor) and every custom widget in it comes over with its code, the settings you made there and
   where it sat. It needs your StreamElements token (Connections → StreamElements) and only reads.
   Or **New widget**: give it a name (letters, digits, `_`, `-`) and paste the four parts into their tabs. Save.
   *Add the example* makes a small one to try and to read.
2. **Open**: a preview (the real page, as on a 1920 × 1080 canvas), **Test** buttons (Follow, Sub, Cheer, Raid,
   Tip), a chat text to test (sent as you, the streamer, so a widget's chat commands like `!spin` can be tried),
   the **Settings** drawn from the widget's FIELDS, and the code.
3. **Add it to OBS**: makes a Browser source `toolbox widget <name>` in the scene you pick, as big as your
   canvas. By hand: a Browser source with the widget's address (`http://127.0.0.1:<port>/overlay/widget/<name>`).

Changing a setting or saving code reloads the widget everywhere, in OBS too.

The files are plain and yours: `config/widgets/<name>/` holds `widget.html`, `widget.css`, `widget.js`,
`fields.json`, `values.json` (your settings) and `store.json` (what the widget's code kept).

Everything a widget gathers while it runs is in its own `data/` folder inside its folder: `store.json` (what its code kept), `channels.json` and `emotes.json` (looked-up answers). The **Data** tab of the widget's window lists it and removes all of it in one click; the code and your settings stay.

## Elements (StreamElements' newer kind)

The **Elements** tab on StreamElements (scene packages with "latest follower" labels and alerts, tickers) holds
a different kind of widget: an Element has no code of its own. It is a settings file: a canvas size and a list
of *states*, each with pictures, videos, sounds and texts that have a place, a look and an animation. A state is
always there (background, labels) or is shown when an event fits it (follow, sub, tip, cheer, raid, gifted subs).

**Import from StreamElements** lists your Elements next to your overlays (or paste an Element's address from
their editor, `https://widgets.streamelements.com/widgets/editor/…/…`). It comes over as it is *published*
there and becomes an ordinary widget in the list:

- The toolbox's own page code draws it (`static/overlay/element.js`); nothing of StreamElements' runs.
- Its pictures, videos, sounds and fonts are copied once into `config/widgets/<name>/media/`, so the page loads
  them from this PC and needs neither StreamElements nor Google Fonts afterwards.
- Its settings are the widget's JS part (`TOOLBOX_ELEMENT.show({...})`): texts, places, sizes and colours can be
  changed there by hand. `{event.data.username}`, `{event.data.amount}` and
  `{session.twitch.follower-latest.name}` (also `subscriber`, `cheer`, `tip`, `raid`) are filled in.
- Alerts play one after the other. The Test buttons work as for every widget.
- "Latest follower" comes from Twitch itself (your Twitch login), so it is right from the first page on.
  Latest subscriber, cheer and tip are filled from what the toolbox saw (Twitch has no list for those); that
  is kept in `config/cache/widget_session.json`, so they aren't empty after a restart.
- The `{...}` names in the settings stay as they are: the page fills them in when it draws.

Not there yet: changing an Element in a settings form (edit it on StreamElements and import again, or edit the
JS part), and Elements that bring code of their own (a custom manifest) beyond the field kinds `image`, `video`,
`audio`, `text` and `latestTicker`.

## What the widget's code gets

| StreamElements | Here |
|---|---|
| `{{field}}` in HTML, CSS and JS | filled in with your setting |
| `{field}` in HTML and CSS | filled in too (not in JS: it would hit `const {name} = ...`) |
| `onWidgetLoad` → `obj.detail.fieldData` | your settings |
| `obj.detail.session.data` | this session's data since the toolbox started: `follower-latest`, `subscriber-latest`, `cheer-latest`, `raid-latest`, each with `-session` (`count`, `amount`), `-total` and `-recent` |
| `obj.detail.recents`, `.currency`, `.overlay` | the last 25 events, USD, not in editor mode |
| `obj.detail.channel` | `username` = your Twitch login name, `providerId` = your Twitch id, `id` = your StreamElements account id if the toolbox has your StreamElements token (some widgets ask StreamElements' public API about the channel with it) |
| when `onWidgetLoad` fires | after the whole page has loaded, like on StreamElements, so helper libraries a widget loads (se-tools, jQuery, ...) are ready |
| `onEventReceived` | `follower-latest`, `subscriber-latest` (subs, resubs with `amount` = months, gift subs with `bulkGifted` and `sender`), `cheer-latest`, `raid-latest`, `tip-latest` (see Tips below), `message` (chat), `event:test` (a settings button), `kvstore:update`, and anything a flow sends |
| `onSessionUpdate` | after every follow / sub / cheer / raid |
| jQuery (`$`) | on the page before the widget's code, as on StreamElements (3.7.1, from the toolbox itself; a widget that loads its own gets its own) |
| StreamElements addresses in the code (`api.streamelements.com/...`, `cdn.streamelements.com/...`) | the page never calls them: every `<host>.streamelements.com/<path>` becomes the toolbox's own `/overlay/widget/<name>/streamelements/<host>/<path>`. The page does that by itself when it is shown; **Remove StreamElements links** in the widget's window writes it into the code. Answered there: `api/kappa/v2/channels/<name or id>` (picture, platform, Twitch id) from your Twitch login, kept for six hours, also across restarts (in the widget's data folder, at most 500 channels); `.../channels/<id>/emotes` with the channel's BetterTTV and FrankerFaceZ emotes in StreamElements' old shape (StreamElements removed that endpoint; the toolbox asks BetterTTV and FrankerFaceZ themselves and keeps the answer in the widget's data folder). Everything else is answered the way StreamElements says "not found" (404 with `statusCode`, `error`, `message`), which code written for their API already handles. The switch *Ask StreamElements when the toolbox can't answer* (Widgets tab, off at the start) lets the toolbox ask StreamElements' API for the rest, and lets files from their other hosts load from there |
| `SE_API.store.set / get` | kept in the widget's `data/store.json` |
| `SE_API.sanitize`, `cheerFilter`, `counters.get`, `getOverlayStatus`, `resumeQueue`, `setField` | answer harmlessly so the code keeps running: nothing is filtered, counters are 0 |

Field types in Settings: `text`, `number`, `slider`, `checkbox`, `colorpicker`, `dropdown`, `googleFont` (the
font's name as text), `image-input` / `video-input` / `sound-input` (pick a file on this PC; the code gets an
address it can load), `button` (arrives like on StreamElements: listener `event:test` with the event saying
listener `widget-button`, the field's name and value), `hidden`. Groups open and close like in their editor.

## Tips, and other events the toolbox doesn't hear by itself

A tip is an event in the toolbox like a follow. Two ways in:

- **Connections → StreamElements**: listens to your StreamElements activity feed, so their tips arrive by
  themselves (their dashboard's test buttons too). Its token is your JWT Token in
  `config/streamelements_token.txt`; it only listens. Everything else in that feed (store redemptions, merch,
  charity donations) starts flows through the trigger **StreamElements activity**.
- **Connections → Streamlabs**: listens to your Streamlabs socket (token: your Socket API Token in
  `config/streamlabs_token.txt`; it can only listen). Donations arrive as tips, and so do YouTube Super Chats
  and Super Stickers if YouTube is linked to your Streamlabs account. Everything else (store redemptions,
  merch, Twitch charity donations, YouTube memberships and gifts) starts flows through the trigger **Streamlabs
  activity**, which also says the platform.
- For any other service, whatever hears of a tip tells the toolbox:

- The box **Tips → Tip came in** (`tip.fire`: user, amount, currency, message, source). From a flow, from SAMMI,
  or from any program over the API:
  `curl -X POST http://127.0.0.1:8850/action/tip.fire -d '{"user": "Kit", "amount": 5, "currency": "EUR"}'`
- What happens then: flows with a **Tip** trigger start (they get user, amount, currency, message, platform),
  the **Tip** alert shows if it's on (Overlay → Alerts), and widgets get `tip-latest`.

For anything else a widget listens to (a host, a merch sale, a name of your own): the box **Widgets → Send event
to widgets** sends it from a flow, to one widget or all of them.

## What isn't there

- StreamElements' own services: their store and merch, their bot's counters and commands, their web API (a
  widget that calls `api.streamelements.com` with your channel's key gets nothing). Tips only as above.
- `session.data` from before the toolbox started, and all-time totals: counting starts at each toolbox start.
- Chat messages carry the name, the text, the message id, the user id, the name colour and Twitch's tags that
  say who it is (badges, mod, subscriber). Emote pictures aren't there, so a chat widget shows emotes as their
  words.
- `host-latest` never fires by itself (Twitch has no hosts any more); a flow can send it.

## Latest names (subscriber, cheer, raid, tip)

The toolbox knows the latest follower, the follower count, the subscriber count and the sub points from Twitch. For subs, cheers, raids and tips Twitch has no such list:
the toolbox only knows the ones that came in while it was running (it keeps them over a restart). So a "latest
subscriber" label is empty at first. **Latest names from StreamElements** (Overlay → Widgets) asks
StreamElements once for the ones it knows and keeps them; what the toolbox saw itself is never replaced.

Subs that happened while the toolbox was off are found at the next start: it compares Twitch's list of your
subscribers with the one it saw last. Cheers and raids that happened while it was off are not known to anyone
but Twitch, and Twitch doesn't tell.

## Safety

A widget is someone else's program running in a web page. It can't read files or start anything on your PC;
the browser prevents that. Two fences keep it to itself as well. Both are on for every widget and are set on
the **Safety** tab of the widget's window:

- **Keep it away from the toolbox's own pages.** The widget's page has no identity of its own (the same fence
  StreamElements uses), so its code can't read the toolbox's pages, its API or other widgets. It still reaches
  its own things: its store, its files, its events. Browser storage (`localStorage`, cookies) isn't there for
  it; a stand-in that lasts as long as the page keeps such code running. What a widget keeps with
  `SE_API.store` works as before.
- **Where it may load from and send to.** Only this toolbox, Twitch (`twitch.tv`, `jtvnw.net`: chat widgets
  need it), the hosts the widget's own code names, and hosts you add. Each counts with its subdomains. The tab
  lists the named hosts with a switch each. Anything else is stopped by the browser and shows up under
  **Tried and were stopped** with an **Allow** button: a helper script that starts talking to a new server
  doesn't get through unnoticed.
  - *Only note other hosts* lets everything through and just lists it: for finding out what a widget needs.
  - *Allow every host* switches the list off.

**Everything on this PC.** An import from StreamElements copies what the widget needs to this PC: its code,
the pictures, sounds, videos and fonts it loads from StreamElements' servers, and its helper scripts. The widget
then runs without StreamElements being asked. Before it copies, the toolbox asks you to make sure you may:
files you made or uploaded yourself are yours; files from StreamElements' own library, or from an overlay or
theme someone else made or sold, belong to them. StreamElements' terms allow using their content on
StreamElements only, and a creator's licence may say the same. The toolbox can't check that for you.

**Helper scripts on this PC.** Many widgets load helper scripts and fonts from other people's servers
(`<script src="https://...">`, `<link rel="stylesheet" href="https://...">`). Whoever runs that server decides
what runs in the widget, each time the page opens. An import copies them; for a widget you pasted yourself the
Safety tab lists them (and its StreamElements files) and **Keep them on this PC** fetches
them once into the widget's folder (a style sheet with its fonts), and the page loads those copies from then
on. They don't change any more and the widget works without the internet. **Fetch them again** takes the
current versions, **Load from their servers again** goes back. Your widget's code stays as written. A script
the widget's code loads by itself while it runs isn't in that list; the allowed hosts still cover it.

If a widget stops working after an update of the toolbox: open its Safety tab, look at "Tried and were
stopped", allow what belongs to the widget. If it still doesn't work, switch the first fence off for that
widget.

A third fence is always on and has no switch: **the widget can't send its page to another site.** The address
OBS opens is a small page of the toolbox's own that holds the widget in a frame, and that frame may only show
the widget's page. Popups and embedded sites are stopped as well. A try shows up under "Tried and were
stopped" too.

Still true: an allowed host gets whatever the page sends it (chat, names, the widget's settings). Import only
widgets you trust, and keep OBS up to date (its built-in browser is what runs them). On another device
(phone, tablet) a fenced widget's preview may stay empty; on this PC and in OBS it works.

Plan and background: `docs/PLAN_widget_protection.md`.

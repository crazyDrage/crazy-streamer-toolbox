# Getting told when something happens on stream

**The API has no event feed.** You can't subscribe to follows, redeems or chat from outside, and there is
nothing to poll for new events. The toolbox calls you instead. Three ways:

## 1. A flow that calls your program (works today, no code)

The streamer builds a flow in the dashboard:

- trigger: the event you want (a redeem, a chat command, a follow, a tip, a timer, a key)
- a **Web request** box that sends what you need to your address

In the box's fields the event's data is available as `${event.<field>}`, e.g. `${event.user}`,
`${event.message}`. Your program needs an HTTP address the toolbox can reach.

Fields per event (the common ones, the same on every platform; each also has `platform` and `source`):

| Event | Fields |
|---|---|
| chat | user, user_login, message, command, args, role, user_id, message_id, color, emotes |
| follow | user, user_login, user_id, followed_at |
| sub | user, user_login, user_id, tier, gift |
| resub | user, user_login, user_id, tier, months, message |
| gift | user, user_login, user_id, amount, tier, anonymous |
| cheer | user, user_login, user_id, bits, message, anonymous |
| raid | user, user_login, user_id, viewers |
| redeem | user, user_login, user_id, reward, input, cost, reward_id, redemption_id |
| online / offline | title, category (Twitch: the game; empty on YouTube and Rumble) |
| tip | user, amount, currency, message |
| custom | trigger, platform, source, plus the values the streamer set on the trigger (Triggers → Edit); a trigger without its own values gives user, user_login, input and the fields of the event behind it |

`sub` is per receiver (`gift` = true when it was gifted to them), `gift` is per giver (`amount` = how many):
5 gifted subs are one `gift` and five `sub` with `gift` = true.

The full list, with each platform's own events: `src/streamer_toolbox/core/events/event_fields.py`.

## 2. A plugin (when you need it inside the toolbox)

A plugin can add its own API route (`ctx.add_router`) and its own actions, so a flow can hand events to your
code directly: trigger → your plugin's action. See `docs/PLUGINS.md`. A plugin has no direct door to the
event feed either; the flow is what connects an event to it.

## 3. Asking for a past event

`history.summary` and `history.recent` (over the API) answer what already happened: follows, subs, cheers,
raids, tips, with sums per session / week / month. Good for "who was the last follower", not for reacting
live.

## The other direction

The last event of every kind is kept as a file: `<settings folder>/cache/last_triggers/<event>.json` with
`trigger`, `at`, `data` (the fields above) and, for Twitch, `raw` (the message as Twitch sent it).

Every event, not only the last: Settings → Event recording (off by default). While it is on, each event
is one line with the same four fields in `<settings folder>/cache/events/<YYYY-MM-DD>.jsonl`. Timer ticks
are left out; a day's file is removed after 30 days.

To make the toolbox react to something *you* noticed: run a flow (`flow.<name>`) or `tip.fire`
(`docs/ai/use/actions.md`).

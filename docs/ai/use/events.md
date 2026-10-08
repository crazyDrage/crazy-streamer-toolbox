# Getting told when something happens on stream

**The API has no event feed.** You can't subscribe to follows, redeems or chat from outside, and there is
nothing to poll for new events. The toolbox calls you instead. Three ways:

## 1. A flow that calls your program (works today, no code)

The streamer builds a flow in the dashboard:

- trigger: the event you want (a redeem, a chat command, a follow, a tip, a timer, a key, a custom trigger)
- a **Web request** box that sends what you need to your address

In the box's fields the event's data is available as `${event.<field>}`, e.g. `${event.user}`,
`${event.message}`. Your program needs an HTTP address the toolbox can reach.

Fields per event (the common ones, the same on every platform; each also has `platform` and `source`):

| Event | Fields |
|---|---|
| chat | user, user_login, message, command, args, role, user_id, message_id, color, emotes |
| follow | user, user_login |
| sub | user, user_login, tier, gift |
| resub | user, user_login, tier, months, message |
| gift | user, user_login, amount, tier, anonymous |
| cheer | user, user_login, bits, message, anonymous |
| raid | user, user_login, viewers |
| redeem | user, user_login, reward, input, cost, reward_id, redemption_id |
| online / offline | title |
| tip | user, amount, currency, message |
| custom | trigger, user, user_login, input (plus the fields of the event behind it) |

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

To make the toolbox react to something *you* noticed: `trigger.fire` or `tip.fire`
(`docs/ai/use/actions.md`).

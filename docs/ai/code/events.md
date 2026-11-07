# Adding an event, so something new can start flows

Read `docs/ai/code/rules.md` first. An event is a name plus a dict, published on the `EventBus`. Flows whose
trigger matches start; alerts and widgets listen to the same bus.

## Steps

1. Publish it: `events.publish("<source>.<what>", {...})`, e.g. `"rumble.follow"`. Values are plain text,
   numbers, yes/no, lists. Always include `platform` for anything that comes from a streaming platform.
   A connection with several accounts (Twitch) also gives `account`: which of the streamer's accounts heard it
   (`event_fields.ACCOUNT_FIELD`, added to every `twitch.*` kind); a trigger matches it with
   `{"accounts": "a, b"}` (the editor's Account select, shown when more than one account listens). The name
   `main account` in it (`flow_trigger.MAIN`) is the main account at the time: Twitch events also carry
   `main_account` (no dot of its own). The common events (any platform) carry `account` too (a dot; "" from a
   platform without several accounts); their trigger is the main account's unless it says
   `{"accounts": "all accounts"}` (`flow_trigger.ALL`).
   Follows: a platform that can list its newest followers also runs a `core/followers/FollowerCheck` (setting
   `follower_check`, seconds): it sends the platform's own follow event for each one its `SeenFollowers` list
   (config/followers/) doesn't have, and the live event checks the same list, so each follow comes once.
   Twitch (channels/followers) and YouTube (`youtube.follow`: new subscribers, only public ones; YouTube has no
   live event for them) do; Rumble asks its feed all the time anyway; Fansly can't list followers.
2. List its fields in `EVENT_FIELDS` (`core/events/event_fields.py`). The flow editor shows them as dots on
   the trigger's Start box; a field missing there can't be wired. Keep it in step with the `publish()` call.
3. Make it a trigger the streamer can pick: an entry in `TRIGGER_KINDS` and its one line of help in
   `TRIGGER_INFO` (both in `gui/components/flow_editor/trigger_kinds.py`). The Add trigger window lists it
   under its program (the event's first word; a new program's name goes into `GROUP_TITLES` in
   `trigger_catalog.py` unless its boxes already have one in `CATEGORY_TITLES`).
4. If it is one of the things every platform has (chat, follow, sub, resub, gift, cheer, raid, redeem,
   online, offline), also map it in `CommonEvents` (`core/events/common_events.py`). The common event carries
   `platform` and `source`, and it is what alerts and widgets use for platforms other than Twitch. A flow
   with "follow (any platform)" then works for the new platform without a change.
5. Money from viewers (a donation, a Super Chat, a rant) is also published as `tip`
   (user, amount, currency, message, platform).
6. Test: publish the event on an `EventBus` in a test and check what listens.

## How matching works

- A flow trigger is the event's name plus field patterns (`*` wildcards). Chat triggers have two special
  keys: `words` and `who` (the lowest role that may start it).
- Redeem triggers keep the reward's id, so a renamed reward still matches.
- Every trigger of a flow is a Start box of its own (id t1, t2, ...): the run starts there, and
  `${box.t1.user}` reads its event (empty when another Start box started the run). When two triggers of one
  flow fit an event, the first one starts it.
- Every matching flow starts, side by side. Cooldowns and "when busy" are per flow.

Details: "How a flow gets started" in `docs/ARCHITECTURE.md`.

## Don't

- Don't publish chat text, tokens or anything private into a log while doing it.
- Don't publish the same thing twice under two names unless one is the common event from step 4.
- Events don't leave the toolbox: there is no event feed in the API (`docs/ai/use/events.md`). That is a
  decision, not a gap to fill on the side.

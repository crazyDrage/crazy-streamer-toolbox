"""What each event gives a flow it starts: the keys of its data. Keep this in step with the publish() calls
(TwitchConnection, VtsConnection, TimerClock, KeyboardConnection, TipActions, StreamElementsConnection,
StreamlabsConnection, RumbleNews, youtube_events,
VeadotubeClient, TitsConnection, streamerbot_events, LumiaConnection, HeartRate, tiltify_feed); the flow editor shows them as orange dots on the
Start box."""

EVENT_FIELDS: dict[str, tuple[str, ...]] = {
    # the same on every platform (CommonEvents): each platform's own event below also comes as one of these,
    # with `platform` = where it came from and `source` = the platform's event
    "chat": ("user", "user_login", "message", "command", "args", "role", "user_id", "message_id", "color",
             "emotes", "platform", "source"),
    "follow": ("user", "user_login", "platform", "source"),
    "sub": ("user", "user_login", "tier", "gift", "platform", "source"),
    "resub": ("user", "user_login", "tier", "months", "message", "platform", "source"),
    "gift": ("user", "user_login", "amount", "tier", "anonymous", "platform", "source"),
    "cheer": ("user", "user_login", "bits", "message", "anonymous", "platform", "source"),
    "raid": ("user", "user_login", "viewers", "platform", "source"),
    "redeem": ("user", "user_login", "reward", "input", "cost", "reward_id", "redemption_id", "platform", "source"),
    "online": ("title", "platform", "source"),
    "offline": ("title", "platform", "source"),
    "twitch.redeem": ("user", "user_login", "reward", "input", "cost", "reward_id", "redemption_id", "platform"),
    "twitch.chat": ("user", "user_login", "message", "command", "args", "message_id", "role", "user_id", "color",
                    "emotes", "platform"),
    # a chat message was removed: one (message_id), all of one chatter's (a ban / timeout: no message_id), or
    # the whole chat (no user either)
    "twitch.chat_deleted": ("user", "user_login", "user_id", "message_id", "platform"),
    "twitch.follow": ("user", "user_login", "platform"),
    "twitch.sub": ("user", "user_login", "tier", "gift", "platform"),
    "twitch.resub": ("user", "user_login", "tier", "months", "message", "platform"),
    "twitch.gift": ("user", "user_login", "amount", "tier", "anonymous", "platform"),
    "twitch.cheer": ("user", "user_login", "bits", "message", "anonymous", "platform"),
    "twitch.raid": ("user", "user_login", "viewers", "platform"),
    "twitch.online": ("type", "platform"),
    "twitch.offline": ("platform",),
    "twitch.ad_break": ("seconds", "automatic", "platform"),
    # a tip / donation, told to the toolbox by the Tip came in box (tip.fire); platform = where it came from
    "tip": ("user", "amount", "currency", "message", "platform"),
    # anything in StreamElements' activity feed, by its type (tip, merch, redemption, ...); test = a test button
    "streamelements.activity": ("type", "user", "user_login", "amount", "message", "test", "platform"),
    # anything Streamlabs' socket tells, by its type (donation, merch, loyalty_store_redemption, ...)
    "streamlabs.activity": ("type", "user", "amount", "currency", "message", "product", "test", "platform"),
    # Rumble (RumbleNews): its chat, follows, subs, gifted subs, rants (paid messages; also a tip), live or not
    "rumble.chat": ("user", "message", "command", "args", "role", "platform"),
    "rumble.follow": ("user", "platform"),
    "rumble.sub": ("user", "amount", "platform"),
    "rumble.gift": ("user", "amount", "platform"),
    "rumble.rant": ("user", "amount", "message", "platform"),
    "rumble.online": ("title", "platform"),
    "rumble.offline": ("title", "platform"),
    # YouTube (youtube_events): everything comes through the live chat; a Super Chat / Sticker is also a tip
    "youtube.chat": ("user", "message", "command", "args", "role", "user_id", "message_id", "platform"),
    "youtube.superchat": ("user", "amount", "currency", "message", "platform"),
    "youtube.supersticker": ("user", "amount", "currency", "message", "platform"),
    "youtube.member": ("user", "level", "upgrade", "platform"),
    "youtube.member_milestone": ("user", "months", "level", "message", "platform"),
    "youtube.gift_members": ("user", "amount", "level", "platform"),
    "youtube.online": ("title", "platform"),
    "youtube.offline": ("title", "platform"),
    # a viewer redeemed an event in the Twitch extension "StreamSocket Events" (bits: 0 = free)
    # veadotube mini shows another avatar state (names; previous = the one before)
    "veadotube.state": ("state", "state_id", "previous"),
    "streamsocket.event": ("event", "event_id", "bits", "user", "user_id", "categories", "test", "platform"),
    # T.I.T.S.: something hit the model (item = what was thrown), a trigger started / ended
    "tits.hit": ("item", "item_id", "trigger", "trigger_id", "strength"),
    "tits.trigger_started": ("trigger", "trigger_id"),
    "tits.trigger_ended": ("trigger", "trigger_id"),
    # anything Streamer.bot tells: source + type as it names them ("Kick" + "Follow"); data = all it sent
    "streamerbot.event": ("source", "type", "user", "message", "data"),
    # anything Lumia Stream tells: type (chat, command, alert, ...); alert = the alert's name; data = all it sent
    "lumia.event": ("type", "alert", "origin", "user", "message", "data"),
    # the streamer's heart rate changed (Pulsoid, HypeRate); source = which of them told
    "heartrate": ("bpm", "source"),
    # a donation to the Tiltify campaign (charity: not a tip)
    "tiltify.donation": ("user", "amount", "currency", "message", "campaign", "platform"),
    # Crowd Control: a viewer asked for an effect in the game (status: requested, succeeded, failed)
    "crowdcontrol.effect": ("status", "effect", "effect_id", "game", "user", "target", "seconds", "request_id"),
    "timer": ("every",),
    "vts.model_loaded": ("model", "model_id"),
    "vts.tracking": ("face", "left_hand", "right_hand"),
    "vts.background": ("background",),
    "vts.hotkey": ("hotkey", "hotkey_id", "action", "by_toolbox", "model"),
    "vts.model_config": ("model", "hotkeys_changed"),
    "vts.model_moved": ("model", "x", "y", "rotation", "size"),
    "key.pressed": ("key",),
    # a custom trigger: the source event's fields come along too (a redeem's reward, a chat's message, ...)
    "custom": ("trigger", "platform", "source", "user", "user_login", "input"),
}

# a chat message's "role", lowest to highest; a chat trigger's "who" is the lowest role that may start it
CHAT_ROLES = ("viewer", "sub", "vip", "mod", "broadcaster")

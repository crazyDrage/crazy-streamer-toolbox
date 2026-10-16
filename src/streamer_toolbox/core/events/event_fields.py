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
    "follow": ("user", "user_login", "user_id", "followed_at", "role", "platform", "source"),
    "sub": ("user", "user_login", "user_id", "tier", "gift", "role", "platform", "source"),
    "resub": ("user", "user_login", "user_id", "tier", "months", "message", "role", "platform", "source"),
    "gift": ("user", "user_login", "user_id", "amount", "tier", "anonymous", "role", "platform", "source"),
    "cheer": ("user", "user_login", "user_id", "bits", "message", "anonymous", "role", "platform", "source"),
    "raid": ("user", "user_login", "user_id", "viewers", "role", "platform", "source"),
    "redeem": ("user", "user_login", "user_id", "reward", "input", "cost", "reward_id", "redemption_id", "role",
               "platform", "source"),
    "online": ("title", "category", "platform", "source"),
    "offline": ("title", "category", "platform", "source"),
    "twitch.redeem": ("user", "user_login", "user_id", "reward", "input", "cost", "reward_id", "redemption_id",
                      "role", "platform"),
    "twitch.chat": ("user", "user_login", "message", "command", "args", "message_id", "role", "user_id", "color",
                    "emotes", "platform"),
    # a chat message was removed: one (message_id), all of one chatter's (a ban / timeout: no message_id), or
    # the whole chat (no user either)
    "twitch.chat_deleted": ("user", "user_login", "user_id", "message_id", "role", "platform"),
    "twitch.follow": ("user", "user_login", "user_id", "followed_at", "role", "platform"),
    "twitch.sub": ("user", "user_login", "user_id", "tier", "gift", "role", "platform"),
    "twitch.resub": ("user", "user_login", "user_id", "tier", "months", "message", "role", "platform"),
    "twitch.gift": ("user", "user_login", "user_id", "amount", "tier", "anonymous", "role", "platform"),
    "twitch.cheer": ("user", "user_login", "user_id", "bits", "message", "anonymous", "role", "platform"),
    "twitch.raid": ("user", "user_login", "user_id", "viewers", "role", "platform"),
    "twitch.online": ("type", "title", "category", "platform"),
    "twitch.offline": ("title", "category", "platform"),
    "twitch.ad_break": ("seconds", "automatic", "platform"),
    # a viewer spent bits on a Power-up; kind = message_effect, celebration or gigantify_an_emote; emote =
    # the emote's name where the Power-up has one
    "twitch.power_up": ("user", "user_login", "user_id", "bits", "kind", "message", "emote", "role", "platform"),
    # a chatter Twitch or a mod flagged as suspicious wrote. reason = the heaviest of reasons (ban_evader,
    # banned_in_shared_channel, manually_added); ban_evader = how sure Twitch is (unknown, possible, likely);
    # status = what the mods set for them (monitored, restricted, none)
    "twitch.suspicious_user": ("user", "user_login", "user_id", "message", "message_id", "reason", "reasons",
                               "ban_evader", "status", "role", "platform"),
    # a tip / donation, told to the toolbox by the Tip came in box (tip.fire); platform = where it came from
    "tip": ("user", "amount", "currency", "message", "platform"),
    # anything in StreamElements' activity feed, by its type (tip, merch, redemption, ...); test = a test button
    "streamelements.activity": ("type", "user", "user_login", "amount", "message", "test", "platform"),
    # anything Streamlabs' socket tells, by its type (donation, merch, loyalty_store_redemption, ...)
    "streamlabs.activity": ("type", "user", "amount", "currency", "message", "product", "test", "platform"),
    # Rumble (RumbleNews): its chat, follows, subs, gifted subs, rants (paid messages; also a tip), live or not
    "rumble.chat": ("user", "message", "command", "args", "role", "platform"),
    "rumble.follow": ("user", "followed_at", "role", "platform"),
    "rumble.sub": ("user", "amount", "role", "platform"),
    "rumble.gift": ("user", "amount", "role", "platform"),
    "rumble.rant": ("user", "amount", "message", "role", "platform"),
    "rumble.online": ("title", "platform"),
    "rumble.offline": ("title", "platform"),
    # YouTube (youtube_events): everything comes through the live chat; a Super Chat / Sticker is also a tip
    "youtube.chat": ("user", "message", "command", "args", "role", "user_id", "message_id", "platform"),
    "youtube.superchat": ("user", "amount", "currency", "message", "role", "platform"),
    "youtube.supersticker": ("user", "amount", "currency", "message", "role", "platform"),
    "youtube.member": ("user", "level", "upgrade", "role", "platform"),
    "youtube.member_milestone": ("user", "months", "level", "message", "role", "platform"),
    "youtube.gift_members": ("user", "amount", "level", "role", "platform"),
    "youtube.online": ("title", "platform"),
    "youtube.offline": ("title", "platform"),
    # a viewer redeemed an event in the Twitch extension "StreamSocket Events" (bits: 0 = free)
    # veadotube mini shows another avatar state (names; previous = the one before)
    "veadotube.state": ("state", "state_id", "previous"),
    "streamsocket.event": ("event", "event_id", "bits", "user", "user_id", "categories", "test", "role", "platform"),
    # T.I.T.S.: something hit the model (item = what was thrown; x, y, z = the direction it flew, each -1 to 1),
    # a trigger started / ended
    "tits.hit": ("item", "item_id", "trigger", "trigger_id", "strength", "x", "y", "z"),
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
    "vts.hotkey": ("hotkey", "hotkey_id", "action", "by_plugin", "model"),
    # data = everything VTube Studio sent (modelID, modelName, hotkeyConfigChanged)
    "vts.model_config": ("model", "model_id", "hotkeys_changed", "data"),
    "vts.model_moved": ("model", "x", "y", "rotation", "size"),
    "key.pressed": ("key",),
    # a custom trigger: the source event's fields come along too (a redeem's reward, a chat's message, ...)
    "custom": ("trigger", "platform", "source", "user", "user_login", "input", "role"),
}

# a viewer's "role", lowest to highest. Only a chat message tells it; every other event with "role" above gets
# it from the RoleBook (the role the viewer had in their last chat message). A trigger's "who" is the lowest
# role that may start it, its "who_max" the highest
CHAT_ROLES = ("viewer", "sub", "vip", "mod", "broadcaster")

"""The triggers a flow can start on. A plugin adds its own to these tables (PluginContext.add_trigger)."""
from streamer_toolbox.connections.twitch.eventsub_events import POWER_UPS, SUSPICIOUS_REASONS
from streamer_toolbox.core.actions.registered_action import OptionsProvider
from streamer_toolbox.core.connections.left_out import gone, left_out
from streamer_toolbox.core.testing.test_item import TRIGGER
from streamer_toolbox.core.testing.test_view import TestView
from streamer_toolbox.gui.components.flow_editor.action_picker import SwitchedOff

# kind: (icon, name, the event field it matches, value for a new one); no field = it has nothing to filter by
TRIGGER_KINDS = {  # every platform at once (CommonEvents); the platform's own ones follow
                 "chat": ("chat", "Chat message (any platform)", "command", "!command"),
                 "follow": ("favorite", "Follow (any platform)", "user", "*"),
                 "sub": ("star", "Sub (any platform)", "user", "*"),
                 "resub": ("star_half", "Resub (any platform)", "user", "*"),
                 "gift": ("redeem", "Gift subs (any platform)", "user", "*"),
                 "cheer": ("diamond", "Cheer (any platform)", "user", "*"),
                 "raid": ("groups", "Raid (any platform)", "user", "*"),
                 "redeem": ("redeem", "Redeem (any platform)", "reward", "*"),
                 "online": ("sensors", "Stream online (any platform)", "platform", "*"),
                 "offline": ("sensors_off", "Stream offline (any platform)", "platform", "*"),
                 "twitch.redeem": ("redeem", "Redeem", "reward", ""),
                 "twitch.chat": ("chat", "Chat message", "command", "!command"),
                 "twitch.chat_deleted": ("speaker_notes_off", "Chat message deleted", "user", "*"),
                 "twitch.follow": ("favorite", "Follow", "user", "*"),
                 "twitch.sub": ("star", "Sub", "user", "*"),
                 "twitch.resub": ("star_half", "Resub", "user", "*"),
                 "twitch.gift": ("redeem", "Gift subs", "user", "*"),
                 "twitch.cheer": ("diamond", "Cheer (bits)", "user", "*"),
                 "twitch.raid": ("groups", "Raid", "user", "*"),
                 "tip": ("payments", "Tip", "user", "*"),
                 "streamelements.activity": ("volunteer_activism", "StreamElements activity", "type", "merch"),
                 "streamlabs.activity": ("savings", "Streamlabs activity", "type", "merch"),
                 "streamsocket.event": ("extension", "StreamSocket event", "event_id", "*"),
                 "youtube.chat": ("chat", "YouTube chat message", "command", "!command"),
                 "youtube.superchat": ("payments", "YouTube Super Chat", "user", "*"),
                 "youtube.supersticker": ("payments", "YouTube Super Sticker", "user", "*"),
                 "youtube.member": ("star", "YouTube new member", "user", "*"),
                 "youtube.member_milestone": ("star_half", "YouTube member milestone", "user", "*"),
                 "youtube.gift_members": ("redeem", "YouTube gifted memberships", "user", "*"),
                 "youtube.online": ("sensors", "YouTube stream online", "title", "*"),
                 "youtube.offline": ("sensors_off", "YouTube stream offline", "title", "*"),
                 "rumble.chat": ("chat", "Rumble chat message", "command", "!command"),
                 "rumble.follow": ("favorite", "Rumble follow", "user", "*"),
                 "rumble.sub": ("star", "Rumble sub", "user", "*"),
                 "rumble.gift": ("redeem", "Rumble gift subs", "user", "*"),
                 "rumble.rant": ("payments", "Rumble rant", "user", "*"),
                 "rumble.online": ("sensors", "Rumble stream online", "title", "*"),
                 "rumble.offline": ("sensors_off", "Rumble stream offline", "title", "*"),
                 "twitch.online": ("sensors", "Stream online", "type", "*"),
                 # no field: Twitch says nothing about a stream that ended (its "type" was always empty)
                 "twitch.offline": ("sensors_off", "Stream offline", "", ""),
                 "twitch.ad_break": ("timer", "Ad break", "seconds", "*"),
                 "twitch.power_up": ("auto_awesome", "Power-up used", "kind", "*"),
                 "twitch.suspicious_user": ("gpp_maybe", "Suspicious user wrote", "reason", "*"),
                 "timer": ("timer", "Timer (seconds)", "every", "10"),
                 "vts.model_loaded": ("face", "Model loaded", "model", "*"),
                 "vts.tracking": ("visibility", "Tracking found / lost", "face", "*"),
                 "vts.background": ("wallpaper", "VTS background changed", "background", "*"),
                 "fansly.chat": ("chat", "Fansly chat message", "command", "!command"),
                 "fansly.tip": ("payments", "Fansly tip", "user", "*"),
                 "fansly.sub": ("star", "Fansly sub", "user", "*"),
                 "vts.hotkey": ("bolt", "VTS hotkey fired", "hotkey", "*"),
                 "vts.model_config": ("tune", "VTS model settings changed", "model", "*"),
                 "vts.model_moved": ("open_with", "Model moved", "model", "*"),
                 "veadotube.state": ("face_retouching_natural", "veadotube state changed", "state", "*"),
                 "tits.hit": ("sports_baseball", "T.I.T.S. model was hit", "item", "*"),
                 "tits.trigger_started": ("play_circle", "T.I.T.S. trigger started", "trigger", "*"),
                 "tits.trigger_ended": ("stop_circle", "T.I.T.S. trigger ended", "trigger", "*"),
                 "streamerbot.event": ("precision_manufacturing", "Streamer.bot event", "type", "Follow"),
                 "lumia.event": ("lightbulb", "Lumia event", "type", "alert"),
                 "heartrate": ("monitor_heart", "Heart rate changed", "bpm", "*"),
                 "tiltify.donation": ("volunteer_activism", "Tiltify donation", "user", "*"),
                 "crowdcontrol.effect": ("sports_esports", "Crowd Control effect", "effect", "*"),
                 "key.pressed": ("keyboard", "Key", "key", "f23")}

# kind → one line for the Add trigger window (a kind without one shows only what it gives)
TRIGGER_INFO: dict[str, str] = {
    "chat": "A chat message on any connected platform: a command, a word in it, or a pattern",
    "follow": "Someone followed, on any connected platform",
    "sub": "A new sub or member, on any connected platform",
    "resub": "Someone shared another month, on any connected platform",
    "gift": "Someone gifted subs or memberships, on any connected platform",
    "cheer": "Someone cheered (Twitch bits; the other platforms have no cheers so far)",
    "raid": "Another channel raided, on any connected platform",
    "redeem": "A viewer redeemed something: channel points or a StreamSocket event",
    "online": "The stream went live, on any connected platform; with its title and category (Twitch: the game)",
    "offline": "The stream ended, on any connected platform; with its title and category (Twitch: the game)",
    "twitch.redeem": "A viewer redeemed a channel point reward: pick the reward",
    "twitch.chat": "A message in your Twitch chat: a command, a word in it, or a pattern",
    "twitch.chat_deleted": "A message was removed, all of one chatter's (ban / timeout), or the whole chat",
    "twitch.follow": "Someone followed on Twitch",
    "twitch.sub": "Someone got a new sub on Twitch; gift = yes when it was gifted to them (once per receiver)",
    "twitch.resub": "Someone shared their resub, with the months and their message",
    "twitch.gift": "Someone gave subs away (once per giver); amount = how many. Each receiver also starts Sub",
    "twitch.cheer": "Someone cheered bits",
    "twitch.raid": "Another channel raided you, with its viewers",
    "twitch.online": "Your Twitch stream went live; with its title and category (the game)",
    "twitch.offline": "Your Twitch stream ended; with its title and category (the game)",
    "twitch.ad_break": "An ad break started; seconds = how long",
    "twitch.power_up": "A viewer spent bits on a Power-up: a message effect, a celebration or a gigantified "
                       "emote (kind); with the bits and the emote's name",
    "twitch.suspicious_user": "A chatter Twitch or a mod flagged as suspicious wrote in chat; reason = why "
                              "(ban_evader, banned_in_shared_channel, manually_added), ban_evader = how sure "
                              "Twitch is (possible, likely). Needs a new Connect once",
    "tip": "A tip / donation came in, from any service that tells the toolbox about one",
    "streamelements.activity": "Anything in StreamElements' activity feed, by its type (tip, merch, ...)",
    "streamlabs.activity": "Anything Streamlabs tells, by its type (donation, merch, ...)",
    "streamsocket.event": "A viewer redeemed an event in the StreamSocket Events extension; event_id = the "
                          "event's id as the extension names it (* = every event)",
    "youtube.chat": "A message in your YouTube live chat: a command, a word in it, or a pattern",
    "youtube.superchat": "A paid message in your YouTube chat",
    "youtube.supersticker": "A paid sticker in your YouTube chat",
    "youtube.member": "A new channel member",
    "youtube.member_milestone": "A member shared a milestone, with the months",
    "youtube.gift_members": "Someone gifted memberships; amount = how many",
    "youtube.online": "Your YouTube stream went live",
    "youtube.offline": "Your YouTube stream ended",
    "fansly.chat": "A message in your Fansly chat: a command, a word in it, or a pattern",
    "fansly.tip": "A tip in your Fansly chat, with its message (amount in dollars)",
    "fansly.sub": "A new sub on Fansly, with the tier's name",
    "rumble.chat": "A message in your Rumble chat: a command, a word in it, or a pattern",
    "rumble.follow": "Someone followed on Rumble",
    "rumble.sub": "A new sub on Rumble",
    "rumble.gift": "Someone gifted subs on Rumble",
    "rumble.rant": "A paid message (rant) on Rumble",
    "rumble.online": "Your Rumble stream went live",
    "rumble.offline": "Your Rumble stream ended",
    "timer": "Again and again, every so many seconds",
    "vts.model_loaded": "A model was loaded in VTube Studio",
    "vts.tracking": "The face or a hand was found or lost",
    "vts.background": "VTube Studio shows another background",
    "vts.hotkey": "A hotkey ran in VTube Studio. by_plugin: true = a program pressed it (the toolbox, SAMMI, a "
                  "deck, ...), false = you pressed its key or clicked it in VTube Studio",
    "vts.model_config": "The loaded model's settings changed",
    "vts.model_moved": "The model was moved, turned or resized. Comes many times a second while it moves: give "
                       "the flow a Cooldown (e.g. 0.5 s) to start it less often",
    "veadotube.state": "veadotube mini shows another avatar state",
    "tits.hit": "A thrown item hit the model; with the item, how hard (strength) and from where (x, y, z)",
    "tits.trigger_started": "A T.I.T.S. trigger started",
    "tits.trigger_ended": "A T.I.T.S. trigger ended",
    "streamerbot.event": "Anything Streamer.bot tells, by its type (Follow, ...)",
    "lumia.event": "Anything Lumia Stream tells, by its type (chat, command, alert, ...)",
    "heartrate": "Your heart rate changed (Pulsoid or HypeRate): any change, or only higher than, lower than, "
                 "equal to a number, or once when it rises above / falls below it",
    "tiltify.donation": "A donation to your Tiltify campaign (charity, not a tip)",
    "crowdcontrol.effect": "A viewer asked for an effect in the game",
    "key.pressed": "A key on this PC was pressed, e.g. f23",
}

# the kinds whose field is a number: the editor asks "any / higher than / lower than / equal to" and the number
NUMBER_TRIGGERS = {"heartrate"}

# kind → the choices for the field it is matched on (a dropdown; typing still works). The flow editor page
# brings the ones that ask a service (the Twitch rewards); these are the ones plugins add.
TRIGGER_CHOICES: dict[str, OptionsProvider] = {}


async def _power_ups() -> list[str]:
    return ["*", *POWER_UPS]


async def _suspicious_reasons() -> list[str]:
    return ["*", *SUSPICIOUS_REASONS]


TRIGGER_CHOICES.update({"twitch.power_up": _power_ups, "twitch.suspicious_user": _suspicious_reasons})


def offered_triggers(switched_off: SwitchedOff | None,
                     view: TestView | None = None) -> dict[str, tuple[str, str, str, str]]:
    """The triggers a flow can get now: not those of a connection this copy leaves out, nor of one that is
    switched off (like its boxes in the Add box window), nor those his checks hide (`view`, Settings → What
    you see). A flow keeps the ones it already has."""
    off = set(switched_off()) if switched_off else set()
    return {kind: entry for kind, entry in TRIGGER_KINDS.items() if not left_out(kind) and not gone(kind, off)
            and (view is None or view.shows_key(f"{TRIGGER}:{kind}"))}

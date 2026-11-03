from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_value import EventValue as V

# the event types that come with the toolbox (his round 78 answer 3 a), hidden until something uses them. Their
# values are named like the trigger's fields, so a default flow wires them 1:1; "also known as" is what
# StreamElements' widget code reads (onEventReceived's listener and obj.detail.event.<value>).
DEFAULTS: tuple[EventType, ...] = tuple(EventType(name, values, aka, default=True, hidden=True) for name, values, aka in (
    ("chat", (V("user", also_known_as=("displayName",)), V("message", also_known_as=("text",)),
              V("color", "#ffffff", "colour", ("displayColor",)), V("role"), V("platform"),
              V("user_id", also_known_as=("userId",)), V("message_id", also_known_as=("msgId",)), V("emotes")),
     ("message",)),
    ("chat_deleted", (V("message_id", also_known_as=("msgId",)), V("user_id", also_known_as=("userId",))),
     ("delete-message",)),
    ("follow", (V("user", also_known_as=("name",)), V("platform")), ("follower-latest",)),
    ("sub", (V("user", also_known_as=("name",)), V("tier", "1", "number", ("tier",)),
             V("gift", "false", "yes_no", ("gifted",)), V("platform")), ("subscriber-latest",)),
    ("resub", (V("user", also_known_as=("name",)), V("tier", "1", "number", ("tier",)),
               V("months", "1", "number", ("amount",)), V("message", also_known_as=("message",)), V("platform")),
     ("subscriber-latest",)),
    ("gift", (V("user", also_known_as=("sender",)), V("amount", "1", "number", ("amount",)),
              V("tier", "1", "number", ("tier",)), V("platform")), ("subscriber-latest",)),
    ("cheer", (V("user", also_known_as=("name",)), V("bits", "100", "number", ("amount",)),
               V("message", also_known_as=("message",)), V("platform")), ("cheer-latest",)),
    ("raid", (V("user", also_known_as=("name",)), V("viewers", "1", "number", ("amount",)), V("platform")),
     ("raid-latest",)),
    ("tip", (V("user", also_known_as=("name",)), V("amount", "5", "number", ("amount",)), V("currency"),
             V("message", also_known_as=("message",)), V("platform")), ("tip-latest",)),
    ("redeem", (V("user", also_known_as=("name",)), V("reward"), V("input"), V("platform")), ()),
))

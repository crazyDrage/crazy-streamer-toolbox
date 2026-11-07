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
    # one message (delete-message); every message of one chatter (delete-messages, a ban or timeout)
    ("chat_deleted", (V("message_id", also_known_as=("msgId",)), V("user_id", also_known_as=("userId",))),
     ("delete-message", "delete-messages")),
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
    # added 2026-11-05 for imported widgets (his "add the missing events"). A gift bomb as StreamElements' newer
    # widgets hear it (their widget runtime names communityGiftPurchase-latest; the shape is the gifter's
    # subscriber-latest one, isCommunityGift added)
    ("community_gift", (V("user", also_known_as=("name", "sender")), V("amount", "5", "number", ("amount",)),
                        V("tier", "1", "number", ("tier",)), V("platform")), ("communityGiftPurchase-latest",)),
    # YouTube in StreamElements' words: a Super Chat and a new member (a YouTube "sponsor"). Not on their
    # docs page (it lists Twitch's); the names YouTube widgets for StreamElements listen for
    ("superchat", (V("user", also_known_as=("name",)), V("amount", "5", "number", ("amount",)),
                   V("currency", also_known_as=("userCurrency",)), V("message", also_known_as=("message",)),
                   V("platform")), ("superchat-latest",)),
    ("member", (V("user", also_known_as=("name",)), V("level", also_known_as=("tier",)), V("platform")),
     ("sponsor-latest",)),
    # StreamElements' own activities (their feed: Connections → StreamElements), heard as <type>-latest
    ("charity", (V("user", also_known_as=("name",)), V("amount", "5", "number", ("amount",)),
                 V("message", also_known_as=("message",)), V("platform")), ("charityCampaignDonation-latest",)),
    ("merch", (V("user", also_known_as=("name",)), V("amount", "1", "number", ("amount",)),
               V("message", also_known_as=("message",)), V("platform")), ("merch-latest",)),
))

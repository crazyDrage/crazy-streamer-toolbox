"""The info text of the emoji dictionary (his 2026-11-16: "It should have an info text of how to use the emoji
dictionary"), the same in an event list's text cell and an alert's text."""

EMOJI_HELP = (
    "An emoji dictionary turns words into pictures: each word and the address of its picture, "
    "`{\"Kappa\": \"https://…/kappa.png\"}`.\n\n"
    "- A flow gives it to the event as one of its values, e.g. `emoji_dict` (Overlay → Events). For Twitch chat "
    "the box **Twitch pfp and chat emotes** (or **Twitch emotes**) makes it from the message's emotes.\n"
    "- Pick that value here: every word of the text that is in the dictionary shows as its picture.\n"
    "- Only whole words, with their capitals: `Kappa` becomes the picture, `kappa` and `Kappas` stay words.\n"
    "- An address can be a web address or a path on this PC. A picture that doesn't load shows the word again.")

def chat_command(text: str) -> tuple[str, str]:
    """A chat message as (command, args): "!So ann  now" → ("!so", "ann  now"). A message that doesn't start with
    "!" is no command and has no args, so both are empty (the whole text is in the event's `message`)."""
    first, _, rest = text.strip().partition(" ")
    if not first.startswith("!"):
        return "", ""
    return first.casefold(), rest.strip()

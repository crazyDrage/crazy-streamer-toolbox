from streamer_toolbox.connections.discord.boxes.discord_box import Post
from streamer_toolbox.connections.discord.boxes.post_to_discord import PostToDiscord
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class DiscordActions:
    """Discord's box: a message into the channel the webhook belongs to ("I'm live", a clip's address).
    Names in the text don't ping anyone unless the box says so, so a viewer's words can't call @everyone.

    One Box class per box, in boxes/."""

    def __init__(self, post: Post) -> None:
        self._post = post

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (PostToDiscord(self._post),):
            actions.add_box(box, "discord")

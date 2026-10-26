from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.twitch.boxes.get_viewer_role import GetViewerRole
from streamer_toolbox.connections.twitch.boxes.twitch_viewer_box import Helix
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from collections.abc import Callable



class TwitchViewerActions:
    """"Get viewer role": asks Twitch what a viewer is in the channel: broadcaster, mod, VIP, sub or plain
    viewer. Twitch has no single "role of this user" request, so it asks three small ones (is this user one
    of my moderators / my VIPs / my subscribers) at the same time; the highest one is the role.

    A trigger never asks Twitch (it only has what the event says, and the role of the viewer's last chat
    message): a flow that needs the exact role of someone who didn't write yet uses this box.

    One Box class per box, in boxes/."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken]) -> None:
        self._helix = helix
        self._me = me

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetViewerRole(self._helix, self._me),):
            actions.add_box(box, "twitch")

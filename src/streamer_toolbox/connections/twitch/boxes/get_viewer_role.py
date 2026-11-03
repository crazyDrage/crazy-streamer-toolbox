import asyncio
from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_viewer_box import TwitchViewerBox, SCOPES, _first, _tier


class GetViewerRole(TwitchViewerBox):
    name = "viewer_role"
    label = "Get viewer role"
    help = "What a viewer is in your channel, asked from Twitch now: broadcaster, mod, vip, sub or viewer (the " \
           "highest one), and each as yes / no. Works for someone who never wrote in chat"
    group = "Viewers"
    live = True
    outputs = {"role": "text", "is_mod": "yes/no", "is_vip": "yes/no", "is_sub": "yes/no",
               "tier": "number"}
    hints = {"user": "The viewer's name; not needed with a user id",
             "user_id": "Wire the trigger's user_id into it: saves the look-up by name"}

    async def run(self, user: str = "", user_id: str = "") -> dict[str, Any]:
        missing = [scope for scope in SCOPES if scope not in self._me().scopes]
        if missing:
            raise PermissionError("Twitch hasn't allowed this for the toolbox yet: press Connect once under "
                                  "Connections → Twitch and allow it in the browser (it needs "
                                  f"{', '.join(missing)})")
        me = self._me().user_id
        viewer = str(user_id if user_id is not None else "").strip() or await self._id(user)
        if viewer == me:
            return {"role": "broadcaster", "is_mod": True, "is_vip": False, "is_sub": False, "tier": 0}
        ask = {"broadcaster_id": me, "user_id": viewer}
        mod, vip, sub = (_first(a) for a in await asyncio.gather(
            self._helix("GET", "moderation/moderators", params=ask),
            self._helix("GET", "channels/vips", params=ask), self._helix("GET", "subscriptions", params=ask)))
        role = "mod" if mod else "vip" if vip else "sub" if sub else "viewer"
        return {"role": role, "is_mod": bool(mod), "is_vip": bool(vip), "is_sub": bool(sub),
                "tier": _tier(sub.get("tier")) if sub else 0}

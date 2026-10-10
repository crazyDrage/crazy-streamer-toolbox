import json
from urllib.parse import parse_qs

import httpx

SCOPES = ["channel:read:redemptions", "channel:manage:redemptions", "user:read:chat", "user:write:chat",
          "moderator:read:followers", "channel:read:subscriptions", "bits:read", "channel:read:ads",
          "channel:manage:broadcast"]


class FakeTwitch:
    """Answers like id.twitch.tv (token, validate) and api.twitch.tv/helix; use `transport` with httpx.
    Tokens in `valid` are accepted; refreshing hands out "access-2", "access-3", ..."""

    def __init__(self, client_id: str = "cid") -> None:
        self.client_id = client_id
        self.valid = {"access-1"}
        self.refresh_ok = True
        self.requests: list[httpx.Request] = []
        self.subscriptions: list[dict] = []
        self.chat: list[dict] = []
        self.rewards = [{"id": "r1", "title": "Big Action: clean screen", "cost": 500}]
        self.updates: list[tuple[str, dict]] = []
        self.refused: set[str] = set()  # subscription types Twitch says no to (e.g. subs before affiliate)
        self.redemptions: list[tuple[dict, dict]] = []
        self.markers: list[dict] = []
        self.device_asks_until_confirmed = 0  # how often "did he confirm?" is answered "not yet"
        self.device_scopes = ""
        self.scopes = list(SCOPES)  # what a login is given and has
        self._next = 2

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/oauth2/device":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.device_scopes = form["scopes"]
            return httpx.Response(200, json={"device_code": "dev-1", "user_code": "ABCDEFGH", "interval": 0,
                                             "expires_in": 1800,
                                             "verification_uri": "https://www.twitch.tv/activate?device-code=ABCDEFGH"})
        if path == "/oauth2/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            if form["grant_type"].endswith("device_code"):
                if form.get("device_code") != "dev-1":
                    return httpx.Response(400, json={"status": 400, "message": "invalid device code"})
                if self.device_asks_until_confirmed > 0:
                    self.device_asks_until_confirmed -= 1
                    return httpx.Response(400, json={"status": 400, "message": "authorization_pending"})
            if form["grant_type"] == "refresh_token" and not self.refresh_ok:
                return httpx.Response(400, json={"message": "Invalid refresh token"})
            token = f"access-{self._next}"
            self._next += 1
            self.valid.add(token)
            return httpx.Response(200, json={"access_token": token, "refresh_token": f"refresh-{self._next}",
                                             "expires_in": 14000, "scope": self.scopes})
        if path == "/oauth2/validate":
            token = request.headers["Authorization"].removeprefix("OAuth ")
            if token not in self.valid:
                return httpx.Response(401, json={"message": "invalid access token"})
            return httpx.Response(200, json={"client_id": self.client_id, "login": "crazydrage", "user_id": "42",
                                             "scopes": self.scopes, "expires_in": 14000})
        if request.headers.get("Authorization", "").removeprefix("Bearer ") not in self.valid:
            return httpx.Response(401, json={"message": "Invalid OAuth token"})
        body = json.loads(request.content) if request.content else {}
        if path == "/helix/eventsub/subscriptions":
            if body["type"] in self.refused:
                return httpx.Response(403, json={"message": "subscription missing proper authorization"})
            self.subscriptions.append(body)
            return httpx.Response(202, json={"data": [{"id": "sub1", "status": "enabled"}]})
        if path == "/helix/chat/messages":
            self.chat.append(body)
            return httpx.Response(200, json={"data": [{"message_id": "m1", "is_sent": True}]})
        if path == "/helix/channel_points/custom_rewards/redemptions":
            self.redemptions.append((dict(request.url.params), body))
            return httpx.Response(200, json={"data": [{"status": body["status"]}]})
        if path == "/helix/channels" and request.method == "GET":
            return httpx.Response(200, json={"data": [{"title": "Lizard time", "game_name": "Just Chatting"}]})
        if path == "/helix/streams/markers":
            self.markers.append(body)
            return httpx.Response(200, json={"data": [{"id": "mk1", **body}]})
        if path == "/helix/channel_points/custom_rewards":
            if request.method == "GET":
                if request.url.params.get("only_manageable_rewards") == "true":
                    return httpx.Response(200, json={"data": [r for r in self.rewards if r.get("mine")]})
                return httpx.Response(200, json={"data": self.rewards})
            if request.method == "PATCH":
                self.updates.append((request.url.params["id"], body))
                reward = next((r for r in self.rewards if r["id"] == request.url.params["id"]), None)
                if reward is None or not reward.get("mine"):
                    return httpx.Response(403, json={"message": "The ID in id must be a reward created by client"})
                reward.update(body)
                return httpx.Response(200, json={"data": [reward]})
            if request.method == "DELETE":
                reward = next((r for r in self.rewards if r["id"] == request.url.params["id"]), None)
                if reward is None or not reward.get("mine"):
                    return httpx.Response(403, json={"message": "The ID in id must be a reward created by client"})
                self.rewards.remove(reward)
                return httpx.Response(204)
            reward = {"id": f"r{len(self.rewards) + 1}", **body, "mine": True}  # made by this app
            self.rewards.append(reward)
            return httpx.Response(200, json={"data": [reward]})
        return httpx.Response(404, json={"message": f"not faked: {path}"})

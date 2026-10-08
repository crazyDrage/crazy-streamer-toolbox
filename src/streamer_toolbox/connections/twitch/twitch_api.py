from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError

HELIX = "https://api.twitch.tv/helix"


class TwitchApi:
    """The Helix calls the toolbox uses, as the logged-in streamer. token() gives a fresh access token;
    after a 401 it's asked once more with renew=True (the token was refreshed meanwhile or got revoked)."""

    def __init__(self, client_id: str, token: Callable[..., Awaitable[str]],
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client_id = client_id
        self._token = token
        self._transport = transport

    async def subscribe(self, kind: str, condition: dict[str, str], session_id: str, version: str = "1") -> None:
        """An EventSub subscription delivered to our websocket session."""
        await self._call("POST", "eventsub/subscriptions", json={
            "type": kind, "version": version, "condition": condition,
            "transport": {"method": "websocket", "session_id": session_id}})

    async def rewards(self, broadcaster_id: str, only_mine: bool = False) -> list[dict[str, Any]]:
        """only_mine: just the ones this app created (the ones it may change)."""
        params = {"broadcaster_id": broadcaster_id, **({"only_manageable_rewards": "true"} if only_mine else {})}
        return (await self._call("GET", "channel_points/custom_rewards", params=params))["data"]

    async def create_reward(self, broadcaster_id: str, title: str, cost: int, prompt: str = "",
                            needs_text: bool = False) -> dict[str, Any]:
        return (await self._call("POST", "channel_points/custom_rewards", params={"broadcaster_id": broadcaster_id},
                                 json={"title": title, "cost": cost, "prompt": prompt,
                                       "is_user_input_required": needs_text}))["data"][0]

    async def update_reward(self, broadcaster_id: str, reward_id: str, **changes: Any) -> dict[str, Any]:
        """Only works for rewards this app created (Twitch's rule). Gives the reward as it is now ({} if not)."""
        data = (await self._call("PATCH", "channel_points/custom_rewards",
                                 params={"broadcaster_id": broadcaster_id, "id": reward_id}, json=changes))
        return (data.get("data") or [{}])[0]

    async def add_reward(self, broadcaster_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """A new reward with every setting (TwitchReward.to_api)."""
        return (await self._call("POST", "channel_points/custom_rewards", params={"broadcaster_id": broadcaster_id},
                                 json=body))["data"][0]

    async def delete_reward(self, broadcaster_id: str, reward_id: str) -> None:
        """Only for rewards this app created."""
        await self._call("DELETE", "channel_points/custom_rewards",
                         params={"broadcaster_id": broadcaster_id, "id": reward_id})

    async def set_redemption(self, broadcaster_id: str, reward_id: str, redemption_id: str, status: str) -> None:
        """status FULFILLED (done) or CANCELED (points go back). Only for rewards this app created."""
        await self._call("PATCH", "channel_points/custom_rewards/redemptions",
                         params={"broadcaster_id": broadcaster_id, "reward_id": reward_id, "id": redemption_id},
                         json={"status": status})

    async def create_marker(self, user_id: str, description: str = "") -> dict[str, Any]:
        """A stream marker (only while live)."""
        return (await self._call("POST", "streams/markers", json={
            "user_id": user_id, **({"description": description[:140]} if description else {})}))["data"][0]

    async def send_chat(self, broadcaster_id: str, sender_id: str, message: str) -> None:
        answer = await self._call("POST", "chat/messages", json={
            "broadcaster_id": broadcaster_id, "sender_id": sender_id, "message": message})
        sent = (answer.get("data") or [{}])[0]
        if not sent.get("is_sent", True):
            raise TwitchApiError(400, (sent.get("drop_reason") or {}).get("message", "message not sent"))

    async def helix(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Any Helix call (dev.twitch.tv/docs/api/reference), for the box classes: the answer, {} for 204 No
        Content; a refusal raises TwitchApiError with Twitch's message."""
        return await self._call(method, path, **kwargs)

    async def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._send(method, path, await self._token(), **kwargs)
        if response.status_code == 401:
            response = await self._send(method, path, await self._token(renew=True), **kwargs)
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except ValueError:
                message = response.text
            raise TwitchApiError(response.status_code, message)
        return response.json() if response.content else {}

    async def _send(self, method: str, path: str, token: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(transport=self._transport, timeout=10) as client:
            return await client.request(method, f"{HELIX}/{path}", headers={
                "Client-Id": self._client_id, "Authorization": f"Bearer {token}"}, **kwargs)

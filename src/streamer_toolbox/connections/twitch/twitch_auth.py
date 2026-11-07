from typing import Any

import httpx

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.core.web.web_client import web_client

ID = "https://id.twitch.tv/oauth2"
# the toolbox's own Twitch app ("crazy-streamer-tools", client type Public: it has no secret, so the id may be in
# the code). Used when no app of one's own is filled in; a public app logs in with a code (device code flow)
BUILT_IN_CLIENT_ID = "7fxa6gbrrpfuvxxmdg8tvpj9u6rdf7"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
PENDING = "authorization_pending"
SCOPES = ("channel:read:redemptions", "channel:manage:redemptions", "user:read:chat", "user:write:chat",
          "moderator:read:followers", "channel:read:subscriptions", "bits:read", "channel:read:ads",
          "channel:manage:broadcast")
# asked for at Connect too, but a login without them still works: only the boxes that need one say "press
# Connect once" (TwitchStreamActions). He said yes to all of them (2026-10-03); it's his account
EXTRA_SCOPES = ("clips:edit", "moderator:manage:shoutouts", "moderator:manage:announcements",
                "channel:manage:polls", "channel:manage:predictions", "channel:manage:raids",
                "channel:edit:commercial", "moderator:manage:chat_settings", "moderator:manage:banned_users",
                "moderator:read:chatters",
                # Get viewer role (TwitchViewerActions; his wish 2026-10-10): is this user a mod / a VIP of mine
                "moderation:read", "channel:read:vips",
                # the trigger Suspicious user wrote (his go 2026-10-11): Twitch's "ban evader" note on a chatter
                "moderator:read:suspicious_users")
# a bot account (his answer 119 c: "Bot account" when adding one): writes and reads chat, and does what a mod of his
# channel may (shoutout, announcement, timeout, chat settings, who is in chat). Only permissions the toolbox already
# asks for (rule 43); the first two are needed, the rest are asked for and checked by the boxes that use them
BOT_SCOPES = ("user:read:chat", "user:write:chat", "moderator:manage:shoutouts", "moderator:manage:announcements",
              "moderator:manage:banned_users", "moderator:manage:chat_settings", "moderator:read:chatters")
BOT_NEEDS = ("user:read:chat", "user:write:chat")


class TwitchAuth:
    """Twitch login (dev.twitch.tv/docs/authentication) with the toolbox's own app, a "Public" one without a
    secret: the device code flow. Twitch gives a short code and a page, the streamer confirms the code there
    (any browser where the account is logged in), and the toolbox asks until the tokens are there. A public
    app's refresh token works once: every renewal brings a new one that has to be kept.

    An app of his own (Client ID / Secret, a localhost redirect) is gone since 2026-11-05 (his "we don't need a
    custom one anymore")."""

    def __init__(self, client_id: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client_id = client_id
        self._transport = transport

    async def device(self, scopes: tuple[str, ...] = ()) -> dict[str, Any]:
        """Starts a login with a code: {device_code, user_code, verification_uri, interval, expires_in}. scopes:
        what it asks for (a channel account's: all of them)."""
        async with web_client(self._transport, timeout=10) as client:
            response = await client.post(f"{ID}/device", data={"client_id": self.client_id,
                                                               "scopes": " ".join(scopes or SCOPES + EXTRA_SCOPES)})
        return _json(response)

    async def device_token(self, device_code: str, scopes: tuple[str, ...] = ()) -> dict[str, Any] | None:
        """The tokens once he confirmed the code; None while Twitch still waits for him."""
        try:
            return await self._token({"grant_type": DEVICE_GRANT, "device_code": device_code,
                                      "scopes": " ".join(scopes or SCOPES + EXTRA_SCOPES)})
        except TwitchApiError as e:
            if PENDING in str(e):
                return None
            raise

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        return await self._token({"grant_type": "refresh_token", "refresh_token": refresh_token})

    async def validate(self, access_token: str) -> dict[str, Any]:
        """{client_id, login, user_id, scopes, expires_in}; raises TwitchApiError(401) for a dead token."""
        async with web_client(self._transport, timeout=10) as client:
            response = await client.get(f"{ID}/validate", headers={"Authorization": f"OAuth {access_token}"})
        return _json(response)

    async def _token(self, data: dict[str, str]) -> dict[str, Any]:
        async with web_client(self._transport, timeout=10) as client:
            response = await client.post(f"{ID}/token", data={"client_id": self.client_id, **data})
        return _json(response)


def _json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text
        raise TwitchApiError(response.status_code, message)
    return response.json()

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from streamer_toolbox.core.web.web_client import web_client

API = "https://v5api.tiltify.com"
EVENT = "tiltify.donation"
log = logging.getLogger(__name__)


class TiltifyFeed:
    """Asks Tiltify (v5 API, developers.tiltify.com) for a campaign's new donations again and again; Tiltify
    only pushes to an address on the internet, so asking is the way for a program on a PC. It logs in as the
    streamer's own Tiltify application (client id + secret → a token that can read public things), finds the
    campaign by the user's and the campaign's name in its address, and from then on asks for donations
    completed after the last one it saw. Donations from before it started are not told.

    on_event(data) gets each donation as a `tiltify.donation`; on_state(text) reports "listening" or what
    went wrong. Refused credentials or an unknown campaign stop it (PermissionError / LookupError from
    campaign()). The secret never appears in a message."""

    def __init__(self, client_id: str, secret: str, user: str, campaign: str,
                 on_event: Callable[[dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, every: float = 15.0,
                 transport: httpx.AsyncBaseTransport | None = None, api: str = API) -> None:
        self._client_id = client_id
        self._secret = secret
        self._user = user
        self._campaign = campaign
        self._on_event = on_event
        self._on_state = on_state
        self._every = every
        self._transport = transport
        self._api = api
        self._token = ""
        self._seen: set[str] = set()

    async def campaign(self) -> dict[str, Any]:
        """Logs in and gives the campaign ({"id", "name", ...}). PermissionError if Tiltify refuses the
        application, LookupError if it knows no such campaign, ConnectionError for anything else."""
        self._token = ""
        return await self._get(f"/api/public/campaigns/by/slugs/{self._user}/{self._campaign}")

    async def run(self) -> None:
        """Runs until cancelled, or until Tiltify refuses the application or doesn't know the campaign."""
        since = datetime.now(timezone.utc).isoformat()
        campaign: dict[str, Any] = {}
        while True:
            try:
                campaign = campaign or await self.campaign()
                donations = await self._get(f"/api/public/campaigns/{campaign.get('id')}/donations",
                                            completed_after=since, limit=100)
            except (PermissionError, LookupError) as e:
                self._on_state(str(e))
                return
            except ConnectionError as e:
                log.warning("Tiltify: %s; asking again in %.0f s", e, self._every * 4)
                self._on_state(f"not listening ({e}); trying again")
                await asyncio.sleep(self._every * 4)
                continue
            self._on_state("listening")
            for donation in sorted(donations, key=lambda d: str(d.get("completed_at") or "")):
                if str(donation.get("id")) in self._seen:
                    continue
                self._seen.add(str(donation.get("id")))
                since = max(since, str(donation.get("completed_at") or since))
                try:
                    await self._on_event(tiltify_donation(donation, str(campaign.get("name") or "")))
                except Exception:
                    log.exception("Tiltify: a donation could not be handled")
            await asyncio.sleep(self._every)

    async def _get(self, path: str, **params: Any) -> Any:
        """The `data` of one answer; logs in first, and once more if the token ran out."""
        for fresh in (False, True):
            if fresh or not self._token:
                self._token = await self._login()
            answer = await self._call("GET", path, params=params, headers={"Authorization": f"Bearer {self._token}"})
            if answer.status_code != 401:
                break
        if answer.status_code == 404:
            raise LookupError(f"Tiltify knows no campaign {self._user}/{self._campaign}: both are in the "
                              "campaign's address, tiltify.com/@<user>/<campaign>")
        return self._data(answer)

    async def _login(self) -> str:
        answer = await self._call("POST", "/oauth/token", data={
            "client_id": self._client_id, "client_secret": self._secret, "grant_type": "client_credentials",
            "scope": "public"})
        if answer.status_code in (400, 401, 403):
            raise PermissionError("Tiltify refused the application: check the Client ID on the tab and the "
                                  "secret in its file")
        token = self._body(answer).get("access_token")
        if not token:
            raise ConnectionError("Tiltify gave no token")
        return str(token)

    async def _call(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            async with web_client(self._transport, timeout=10) as client:
                return await client.request(method, self._api + path, **kwargs)
        except httpx.HTTPError as e:
            raise ConnectionError(type(e).__name__) from None

    def _data(self, answer: httpx.Response) -> Any:
        return self._body(answer).get("data")

    @staticmethod
    def _body(answer: httpx.Response) -> dict[str, Any]:
        if answer.status_code != 200:
            raise ConnectionError(f"Tiltify answered {answer.status_code}")
        try:
            body = answer.json()
        except ValueError:
            raise ConnectionError("Tiltify's answer wasn't JSON") from None
        return body if isinstance(body, dict) else {}


def tiltify_donation(donation: dict[str, Any], campaign: str) -> dict[str, Any]:
    """A donation as the toolbox's `tiltify.donation`."""
    amount = donation.get("amount") if isinstance(donation.get("amount"), dict) else {}
    try:
        value = float(amount.get("value") or 0)
    except (TypeError, ValueError):
        value = 0.0
    return {"user": str(donation.get("donor_name") or "Anonymous"), "amount": value,
            "currency": str(amount.get("currency") or ""), "message": str(donation.get("donor_comment") or ""),
            "campaign": campaign, "platform": "tiltify"}

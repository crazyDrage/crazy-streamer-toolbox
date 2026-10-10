import asyncio
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from streamer_toolbox.core.widgets.channel_lookup import ChannelLookup
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers
from streamer_toolbox.core.widgets.latest_followers import LatestFollowers
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback
from streamer_toolbox.core.widgets.subscriber_count import SubscriberCount
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_safety import OWN, host_of
from streamer_toolbox.core.widgets.widget_store import WidgetStore

LOCAL = "/overlay/widget/{name}/streamelements"  # a widget's stand-in for StreamElements' hosts
API = LOCAL + "/api/kappa/v2"  # where StreamElements' public API is there
HOST = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)*")
NO_EMOTES = {"bttvChannelEmotes": {}, "bttvGlobalEmotes": {}, "ffzChannelEmotes": {}, "ffzGlobalEmotes": {}}


def build_widget_router(store: WidgetStore, hub: WidgetHub, page: WidgetPage,
                        channels: ChannelLookup | None = None,
                        fallback: StreamElementsFallback | None = None,
                        emote_lookup: EmoteLookup | None = None,
                        followers: LatestFollowers | None = None,
                        subscribers: SubscriberCount | None = None) -> APIRouter:
    """A widget's overlay for OBS's Browser source: GET /overlay/widget/<name> (a shell page of the toolbox's
    own that holds the widget in a frame and keeps that frame from going to another site), .../page (the page
    built from its parts, served into that frame), .../ws (the page listens for events), .../file/<field> (the picture / video / sound he picked for that field,
    and nothing else from this PC), .../media/<file> (a file of the widget's own media folder) and .../store/<key> (what the widget's code keeps with SE_API.store).
    GET /overlay/widget/<name>/streamelements/<host>/<path>: that widget's stand-in for
    <host>.streamelements.com/<path> (streamelements_links turns the widget's StreamElements addresses into
    these). The answers kept for it are in the widget's own data folder (channels.json, emotes.json). api/kappa/v2/channels/<name
    or id> = who a channel is, from the toolbox's Twitch login (ChannelLookup); .../channels/<id>/emotes =
    its BetterTTV and FrankerFaceZ emotes (EmoteLookup). What the toolbox has no answer for is answered the way
    StreamElements says "not found" (404 with {"statusCode", "error", "message"}), which code written for
    their API already handles. Only with the fallback switch on, the toolbox asks StreamElements' API for
    those and hands the answer on, and a file from another of their hosts (cdn, ...) is fetched from there by
    the page.

    The page comes with the widget's fences as headers (WidgetSafety: sandbox, allowed hosts); what the
    browser stops is told to POST .../blocked. WidgetSandboxMiddleware lets the sandboxed page reach these routes.

    No tokens: the login gate in front of the pages lets this PC in and other devices only once signed in."""
    router = APIRouter()

    @router.get("/overlay/widget/{name}", response_class=HTMLResponse)
    def widget_shell(name: str, request: Request) -> HTMLResponse:
        _widget(store, name)
        safety = store.safety(name)
        own = f"{request.url.scheme}://{request.headers.get('host', '')}"
        return HTMLResponse(page.shell(name, request.url.query, safety.frame_sandbox()),
                            headers={"Cache-Control": "no-store", **safety.shell_headers(name, own)})

    @router.get("/overlay/widget/{name}/page", response_class=HTMLResponse)
    async def widget_page(name: str, request: Request) -> Response:
        widget = _widget(store, name)
        # only into the shell's frame: opened as a page of its own it could send itself anywhere
        if request.headers.get("sec-fetch-dest", "iframe") != "iframe":
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(f"/overlay/widget/{name}{query}")
        # the fences around the widget's code (WidgetSafety): no identity of its own, only the allowed hosts
        fences = store.safety(name).headers(widget, f"{request.url.scheme}://{request.headers.get('host', '')}",
                                            (OWN,) if fallback and fallback.on else ())
        if followers:  # the latest followers as Twitch has them, before the page reads the session data
            await followers.fill(hub.session)
        if subscribers:  # how many subscribers and sub points Twitch counts
            await subscribers.fill(hub.session)
        hub.session.refresh()  # this week / this month, from the toolbox's own record
        return HTMLResponse(page.render(widget, store.helpers(name)), headers={"Cache-Control": "no-store", **fences})

    @router.post("/overlay/widget/{name}/blocked")
    async def blocked(name: str, request: Request) -> dict[str, bool]:
        """The browser tells what it stopped (or, in "only note" mode, would have): kept for the widget's
        window, where he can allow the host."""
        _widget(store, name)
        try:
            report = (await request.json()).get("csp-report", {})
        except (ValueError, AttributeError):
            report = {}
        store.note_blocked(name, host_of(str(report.get("blocked-uri") or "")))
        return {"ok": True}

    @router.get("/overlay/widget/{name}/file/{field}")
    def widget_file(name: str, field: str) -> FileResponse:
        widget = _widget(store, name)
        file = Path(str(widget.field_data().get(field) or "")) if field in widget.media_fields() else None
        if file is None or not file.is_file():
            raise HTTPException(status_code=404, detail="no file for that field")
        return FileResponse(file)

    @router.get("/overlay/widget/{name}/media/{file}")
    def widget_media(name: str, file: str) -> FileResponse:
        path = store.media_file(name, file)
        if path is None:
            raise HTTPException(status_code=404, detail="no such file in that widget's media folder")
        return FileResponse(path)

    @router.get("/overlay/widget/{name}/store/{key}")
    def kept(name: str, key: str) -> Any:
        _widget(store, name)
        return store.kept(name, key)

    @router.put("/overlay/widget/{name}/store/{key}")
    def keep(name: str, key: str, value: Any = Body(default=None)) -> dict[str, bool]:
        _widget(store, name)
        store.keep(name, key, value)
        return {"ok": True}

    async def elsewhere(path: str, missing: str) -> Any:
        answer = await fallback.get(path) if fallback else None
        return answer if answer is not None else _not_found(missing)

    def kept(name: str, file: str, keep_count: int) -> KeptAnswers:
        """The answers kept for that widget, in its data folder (read each time: he may have cleared it)."""
        _widget(store, name)
        return KeptAnswers(store.data_folder(name) / file, keep_count)

    @router.get(API + "/channels/{who}")
    async def channel(name: str, who: str) -> Any:
        answer = await channels.channel(who, kept(name, "channels.json", 500)) if channels else None
        return answer if answer is not None else await elsewhere(f"channels/{who}", f"channel {who} was not found")

    @router.get(API + "/channels/{who}/emotes")
    async def emotes(name: str, who: str) -> Any:
        known = await channels.channel(who, kept(name, "channels.json", 500)) if channels else None
        twitch_id = known["providerId"] if known else who  # a Twitch id works without the Twitch login too
        return await emote_lookup.emotes(twitch_id, kept(name, "emotes.json", 100)) if emote_lookup else NO_EMOTES

    @router.get(API + "/{path:path}")
    async def other_question(name: str, path: str) -> Any:
        return await elsewhere(path, f"the toolbox has no answer for {path}")

    @router.get(LOCAL + "/{host}/{path:path}")
    async def other_host(name: str, host: str, path: str) -> Any:
        kept = store.streamelements_media(name).get(f"{host.casefold()}/{path}")
        if kept:  # a StreamElements file that was copied to this PC (StreamElementsMedia)
            return FileResponse(store.media_file(name, kept))
        if not (fallback and fallback.on and HOST.fullmatch(host)):
            return _not_found(f"the toolbox has nothing for {host}/{path}")
        return RedirectResponse(f"https://{'' if host == 'www' else host + '.'}streamelements.com/{path}")

    @router.websocket("/overlay/widget/{name}/ws")
    async def widget_socket(socket: WebSocket, name: str) -> None:
        await socket.accept()
        inbox = hub.listen(name, preview="preview" in socket.query_params)
        sender = asyncio.create_task(_send(socket, inbox))
        try:
            while True:  # the page sends nothing; this ends when it closes
                await socket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()
            hub.stop_listening(inbox)

    return router


def _not_found(message: str) -> JSONResponse:
    """"Not found" in StreamElements' own words, so code that checks their `error` field sees it."""
    return JSONResponse({"statusCode": 404, "error": "Not Found", "message": message}, status_code=404)


def _widget(store: WidgetStore, name: str):
    widget = store.get(name)
    if widget is None:
        raise HTTPException(status_code=404, detail=f"there's no widget {name}")
    return widget


async def _send(socket: WebSocket, inbox: asyncio.Queue) -> None:
    while True:
        await socket.send_json(await inbox.get())

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

from streamer_toolbox.core.alerts.alert_queue import AlertQueue

PAGE = Path(__file__).parent.parent / "gui" / "static" / "overlay" / "alerts.html"


def build_overlay_router(queue: AlertQueue) -> APIRouter:
    """The overlay for OBS's Browser source: GET /overlay/alerts (a plain see-through page), its socket
    /overlay/alerts/ws (the page listens; the AlertQueue sends each alert when it's its turn) and
    /overlay/file/<token> (an alert's picture or sound, only under the random name the queue gave it).

    No tokens here: the login gate in front of the pages lets this PC in and other devices only once signed in."""
    router = APIRouter()

    @router.get("/overlay/alerts", response_class=HTMLResponse)
    def alerts_page() -> HTMLResponse:
        return HTMLResponse(PAGE.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

    @router.get("/overlay/file/{token}")
    def alert_file(token: str) -> FileResponse:
        file = queue.file(token)
        if file is None or not file.is_file():
            raise HTTPException(status_code=404, detail="no such alert file")
        return FileResponse(file)

    @router.websocket("/overlay/alerts/ws")
    async def alerts_socket(socket: WebSocket) -> None:
        await socket.accept()
        inbox = queue.listen(preview="preview" in socket.query_params)
        sender = asyncio.create_task(_send(socket, inbox))
        try:
            while True:  # the page sends nothing; this ends when it closes
                await socket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()
            queue.stop_listening(inbox)

    return router


async def _send(socket: WebSocket, inbox: asyncio.Queue) -> None:
    while True:
        await socket.send_json(await inbox.get())

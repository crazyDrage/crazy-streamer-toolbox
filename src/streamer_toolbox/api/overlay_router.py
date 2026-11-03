from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import FileResponse, HTMLResponse

from streamer_toolbox.api import overlay_line
from streamer_toolbox.core.alerts.alert_queue import AlertQueue

PAGE = Path(__file__).parent.parent / "gui" / "static" / "overlay" / "alerts.html"


def build_overlay_router(queue: AlertQueue, heartbeat: float = overlay_line.HEARTBEAT) -> APIRouter:
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
        preview = "preview" in socket.query_params
        run, after = overlay_line.resume(socket)
        inbox = queue.listen(preview=preview)
        for message in queue.greeting(run, after):
            inbox.put_nowait(message)
        try:
            await overlay_line.serve(socket, inbox, heartbeat, None if preview else queue.not_arrived,
                                     arrived=queue.arrived)
        finally:
            queue.stop_listening(inbox)

    return router


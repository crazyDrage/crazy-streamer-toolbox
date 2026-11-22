import logging
from collections.abc import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from streamer_toolbox.core.interfaces.message_inbox import MessageInbox

log = logging.getLogger(__name__)
REFUSED = 1008  # the websocket's "policy violation": a wrong key, an unknown connection, switched off


def build_inbound_router(find_inbox: Callable[[str], MessageInbox | None]) -> APIRouter:
    """Programs that send TO the toolbox (MessageInbox): ws://<toolbox>/connections/<id>/in/<type>?key=...
    find_inbox(id) gives the connection's inbox, or None (no such connection, or it takes no messages).
    The key is in the address because the programs that connect in (Warudo's Send Websocket plugin) have only
    an address field; the failed-request log never writes the query."""
    router = APIRouter()

    @router.websocket("/connections/{connection_id}/in/{kind}")
    async def inbound_socket(socket: WebSocket, connection_id: str, kind: str) -> None:
        inbox = find_inbox(connection_id)
        refusal = "no such connection takes messages" if inbox is None else \
            inbox.refusal(socket.query_params.get("key", ""))
        if refusal:
            log.info("inbound line %s/%s refused: %s", connection_id, kind, refusal)
            await socket.close(code=REFUSED, reason=refusal[:120])
            return
        await socket.accept()
        inbox.opened(kind)
        try:
            while True:
                message = await socket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                text = message.get("text")
                if text is None and message.get("bytes") is not None:
                    text = message["bytes"].decode("utf-8", errors="replace")
                if text is not None:
                    inbox.received(kind, text)
        except WebSocketDisconnect:
            pass
        finally:
            inbox.closed(kind)

    return router

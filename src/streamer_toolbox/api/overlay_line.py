"""The line between an overlay page (a Browser source in OBS: the alerts, a widget) and the toolbox.

A line can drop without either side hearing it (a PC that slept, a router or VPN that forgot the connection, a
stalled OBS): the page's socket then says "open" forever and gets nothing (found with temp/alert_soak, his
round 64). So the toolbox says {"type": "alive"} whenever it had nothing else to say for HEARTBEAT seconds; a
page that hears nothing for much longer drops the line and connects again (alerts.js, widget.js).

A page that connects with ?ack=1 answers every message: the toolbox numbers each one ("n") and the page sends
{"type": "got", "n": ...} back. A message without an answer after ACK_WAIT seconds means the line is broken:
the toolbox ends it, and everything the page didn't confirm (sent, or still waiting in the inbox) goes to
`missed`, so the toolbox knows which alert or event didn't reach OBS. "alive" is answered too, so a page that
is gone is noticed within HEARTBEAT + ACK_WAIT seconds, also when nothing else happens. A send that fails ends
the line at once too.

A page that comes back says ?run=...&after=<the last id it got> (core/overlay/SentMessages): resume() reads that,
and the inbox starts with what it missed. A missed message that then arrives goes to `arrived`.
"""
import asyncio
import json
import time
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

HEARTBEAT = 15.0  # seconds; the pages give up after 40 s of nothing
ACK_WAIT = 1.0  # seconds a page has to say it got a message (local: it answers in milliseconds)

Missed = Callable[[dict[str, Any]], None]


def resume(socket: WebSocket) -> tuple[str | None, int | None]:
    """(run, after) of a page that comes back; after is None for a page that connects the first time."""
    after = socket.query_params.get("after", "")
    return socket.query_params.get("run"), int(after) if after.isdigit() else None


async def serve(socket: WebSocket, inbox: asyncio.Queue, heartbeat: float = HEARTBEAT,
                missed: Missed | None = None, ack_wait: float = ACK_WAIT, arrived: Missed | None = None) -> None:
    """Sends what arrives in the inbox (and "alive" in between) until the page closes, a send fails or (a page
    that answers) an answer doesn't come. What the page didn't confirm goes to missed ("alive" doesn't), what it
    confirmed to arrived."""
    acks = socket.query_params.get("ack") == "1"
    waiting: dict[int, tuple[float, dict[str, Any]]] = {}  # n → (sent at, message), until the page answers
    sender = asyncio.create_task(_send(socket, inbox, heartbeat, waiting if acks else None))
    receiver = asyncio.create_task(_receive(socket, waiting, arrived))
    tasks = {sender, receiver}
    if acks:
        tasks.add(asyncio.create_task(_watch(waiting, ack_wait)))
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:  # no await in here: a server shutting down cancels this, and that must end it at once
        for task in tasks:
            task.cancel()
    if receiver not in done:  # a send failed or an answer didn't come: the page is gone
        try:
            await socket.close()
        except Exception:  # it is gone already
            pass
    if acks and missed is not None:
        _report(waiting, inbox, missed)


async def _send(socket: WebSocket, inbox: asyncio.Queue, heartbeat: float,
                waiting: dict[int, tuple[float, dict[str, Any]]] | None) -> None:
    n = 0
    while True:
        try:
            message = await asyncio.wait_for(inbox.get(), heartbeat)
        except TimeoutError:
            message = {"type": "alive"}
        if waiting is not None:
            n += 1
            waiting[n] = (time.monotonic(), message)
            message = {**message, "n": n}
        await socket.send_json(message)


async def _receive(socket: WebSocket, waiting: dict[int, tuple[float, dict[str, Any]]],
                   arrived: Missed | None) -> None:
    try:
        while True:  # the page only says what it got; this ends when it closes
            try:
                told = json.loads(await socket.receive_text())
            except ValueError:
                continue
            if isinstance(told, dict) and told.get("type") == "got" and isinstance(told.get("n"), int):
                sent = waiting.pop(told["n"], None)
                if sent is not None and arrived is not None:
                    arrived(sent[1])
    except WebSocketDisconnect:
        pass


async def _watch(waiting: dict[int, tuple[float, dict[str, Any]]], ack_wait: float) -> None:
    """Ends (and so the line) when a message waited longer than ack_wait for its answer."""
    while True:
        await asyncio.sleep(min(1.0, ack_wait / 5))
        if any(time.monotonic() - sent > ack_wait for sent, _ in waiting.values()):
            return


def _report(waiting: dict[int, tuple[float, dict[str, Any]]], inbox: asyncio.Queue, missed: Missed) -> None:
    unsent = []
    while not inbox.empty():
        unsent.append(inbox.get_nowait())
    for message in [message for _, (_, message) in sorted(waiting.items())] + unsent:
        if message.get("type") != "alive":
            missed(message)

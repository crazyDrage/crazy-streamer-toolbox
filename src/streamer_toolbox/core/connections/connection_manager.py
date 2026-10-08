import asyncio
import logging
from typing import Any

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.connections.connection_status import ConnectionStatus

log = logging.getLogger(__name__)


class ConnectionManager:
    """Starts every enabled connection with the toolbox, and applies GUI changes live (save + reconnect).
    While running it checks every few seconds, so a program started after the toolbox gets connected by itself."""

    def __init__(self, connections: list[Connection], writer: ConfigTableWriter, check_every: float = 5.0) -> None:
        self._connections = {c.id: c for c in connections}
        self._writer = writer
        self._check_every = check_every
        self._busy = {c.id: asyncio.Lock() for c in connections}  # a check never runs during a GUI restart
        self._watcher: asyncio.Task | None = None

    def all(self) -> list[Connection]:
        return list(self._connections.values())

    def get(self, connection_id: str) -> Connection:
        return self._connections[connection_id]

    async def start_all(self) -> None:
        await asyncio.gather(*(self._start(c) for c in self.all() if c.settings["enabled"]))
        self._watcher = asyncio.create_task(self._watch())

    async def stop_all(self) -> None:
        if self._watcher is not None:
            self._watcher.cancel()
            await asyncio.gather(self._watcher, return_exceptions=True)
            self._watcher = None
        await asyncio.gather(*(c.stop() for c in self.all()), return_exceptions=True)

    async def check_all(self) -> None:
        """One round of keep_alive for every switched-on connection (the watcher calls it every few seconds)."""
        await asyncio.gather(*(self._keep_alive(c) for c in self.all() if c.settings["enabled"]))

    async def connect(self, connection_id: str, typed: dict[str, Any]) -> ConnectionStatus:
        """Tests what was typed (empty fields keep the saved value). Only if that works: switch on, save,
        reconnect. A failed test changes nothing."""
        connection = self.get(connection_id)
        settings = {**connection.settings, **{k: v for k, v in typed.items() if v not in (None, "")}, "enabled": True}
        status = await connection.test(settings)
        if not status.ok:
            return status
        self._writer.save(connection.id, settings)
        await self._restart(connection, settings)
        return connection.status

    async def set_enabled(self, connection_id: str, enabled: bool) -> None:
        connection = self.get(connection_id)
        self._writer.save(connection.id, {"enabled": enabled})
        await self._restart(connection, {**connection.settings, "enabled": enabled})

    async def _restart(self, connection: Connection, settings: dict[str, Any]) -> None:
        async with self._busy[connection.id]:
            await connection.stop()
            connection.configure(settings)
            if settings["enabled"]:
                await self._start(connection)

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(self._check_every)
            await self.check_all()

    async def _keep_alive(self, connection: Connection) -> None:
        lock = self._busy[connection.id]
        if lock.locked():
            return
        async with lock:
            try:
                await connection.keep_alive()
            except Exception:  # keep_alive shouldn't raise; the watcher must keep going
                log.exception("%s: keep_alive failed", connection.id)

    @staticmethod
    async def _start(connection: Connection) -> None:
        try:
            await connection.start()
        except Exception:  # start() shouldn't raise; one broken connection mustn't stop the others
            log.exception("%s: start failed", connection.id)

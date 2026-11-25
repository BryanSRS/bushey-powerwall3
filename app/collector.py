"""Background loop that polls the data source and stores readings."""
import asyncio
import logging

from .config import settings
from .powerwall import Snapshot, get_source
from .storage import Storage

log = logging.getLogger(__name__)


class Collector:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.source = None
        self.latest: Snapshot | None = None
        self.last_error: str | None = None

    async def run(self) -> None:
        while True:
            try:
                if self.source is None:
                    self.source = await asyncio.to_thread(get_source)
                snap = await asyncio.to_thread(self.source.read)
                self.latest = snap
                self.last_error = None
                await asyncio.to_thread(self.storage.insert, snap)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # keep running through Wi-Fi drops, reboots, etc.
                log.warning("Read failed: %s", exc)
                self.last_error = str(exc)
                self.source = None  # reconnect on the next pass
            await asyncio.sleep(settings.poll_seconds)

    async def strings(self) -> dict:
        if self.source is None:
            return {}
        return await asyncio.to_thread(self.source.strings)

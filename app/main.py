"""Web server: JSON API plus the data screen page.

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8080
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .collector import Collector
from .config import settings
from .storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

STATIC = Path(__file__).parent / "static"
storage = Storage(settings.db_path)
collector = Collector(storage)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(collector.run())
    yield
    task.cancel()


app = FastAPI(title="Bushey Powerwall", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/live")
def live():
    if collector.latest is None:
        raise HTTPException(503, detail=collector.last_error or "Waiting for the first reading")
    data = collector.latest.to_dict()
    data["mode"] = settings.mode
    data["stale"] = time.time() - collector.latest.ts > settings.poll_seconds * 4
    data["error"] = collector.last_error
    return data


@app.get("/api/history")
def history(hours: float = Query(24, gt=0, le=24 * 31)):
    bucket = 60 if hours <= 6 else 300 if hours <= 48 else 1800
    return storage.history(time.time() - hours * 3600, bucket)


@app.get("/api/strings")
async def strings():
    return await collector.strings()


@app.get("/api/health")
def health():
    return {"mode": settings.mode, "has_reading": collector.latest is not None, "error": collector.last_error}

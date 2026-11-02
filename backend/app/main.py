import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .keepalive import keepalive_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

EVENT_TYPES = {"visit", "selah_click", "order_click"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(keepalive_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Beautiful Nothing API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _clip(value, limit: int) -> str | None:
    return str(value)[:limit] if value else None


@app.post("/api/events", status_code=204)
async def record_event(request: Request, background: BackgroundTasks) -> Response:
    # The frontend sends via navigator.sendBeacon as text/plain (no CORS preflight), so parse manually.
    try:
        payload = json.loads(await request.body())
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "invalid JSON")
    if not isinstance(payload, dict) or payload.get("type") not in EVENT_TYPES:
        raise HTTPException(400, "unknown event type")

    row = {
        "type": payload["type"],
        "visitor_id": _clip(payload.get("visitor_id"), 64),
        "path": _clip(payload.get("path"), 200),
        "referrer": _clip(payload.get("referrer"), 500),
        "user_agent": _clip(request.headers.get("user-agent"), 300),
    }
    background.add_task(db.insert_event, row)
    return Response(status_code=204)


@app.get("/api/health")
async def health() -> dict:
    # Also touches the DB, so an external uptime pinger keeps both the API and Supabase awake.
    try:
        db_ok = await run_in_threadpool(db.ping)
    except Exception:
        db_ok = False
    return {"ok": True, "db": db_ok}

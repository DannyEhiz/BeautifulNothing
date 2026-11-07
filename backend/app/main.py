import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from . import admin, config, db, site
from .keepalive import keepalive_loop
from .web import BASE, render

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

EVENT_TYPES = {"visit", "ebook_click", "showlove_click", "order_click"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not config.ADMIN_EMAILS:
        log.warning("ADMIN_EMAILS is empty — order notifications won't be sent to anyone")
    # These are public links, safe to print — makes "button not going to Selar" easy to diagnose.
    log.info("Sales phase: %s", config.SALES_PHASE)
    log.info("Show love → %s", config.SHOWLOVE_URL or "NOT SET (button shows 'goes live very soon')")
    log.info("Ebook     → %s", config.EBOOK_URL or "NOT SET (button shows 'goes live very soon')")
    task = asyncio.create_task(keepalive_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Beautiful Nothing", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(site.router)
app.include_router(admin.router)


@app.exception_handler(db.NotConfigured)
async def not_configured(request: Request, exc: db.NotConfigured):
    log.error("%s", exc)
    return render(
        request, "message.html", status_code=503,
        heading="Almost ready", text="The site isn't fully set up yet. Please try again a little later.",
    )


@app.exception_handler(db.DBError)
async def db_error(request: Request, exc: db.DBError):
    log.error("Supabase error %s on %s: %s", exc.status, request.url.path, exc)
    if request.url.path.startswith("/api/"):
        return Response(status_code=503)
    return render(
        request, "message.html", status_code=503,
        heading="Something went wrong", text="We couldn't complete that just now. Please try again in a moment.",
    )


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith(("/api/", "/static/")):
        return Response(status_code=404)
    return render(request, "message.html", status_code=404, heading="Page not found", text="That page doesn't exist.")


@app.post("/api/events", status_code=204)
async def record_event(request: Request, background: BackgroundTasks) -> Response:
    # Sent with navigator.sendBeacon as text/plain, so parse the body manually.
    try:
        payload = json.loads(await request.body())
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "invalid JSON")
    if not isinstance(payload, dict) or payload.get("type") not in EVENT_TYPES:
        raise HTTPException(400, "unknown event type")

    def clip(value, limit: int) -> str | None:
        return str(value)[:limit] if value else None

    row = {
        "type": payload["type"],
        "visitor_id": clip(payload.get("visitor_id"), 64),
        "path": clip(payload.get("path"), 200),
        "referrer": clip(payload.get("referrer"), 500),
        "user_agent": clip(request.headers.get("user-agent"), 300),
    }
    background.add_task(db.insert_event, row)
    return Response(status_code=204)


@app.get("/api/health")
async def health() -> dict:
    # Also touches the DB, so an uptime pinger keeps both the app and Supabase awake.
    try:
        db_ok = await db.ping()
    except Exception:
        db_ok = False
    return {"ok": True, "db": db_ok}

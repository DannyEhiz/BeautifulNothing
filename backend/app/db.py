import logging

from supabase import Client, create_client

from . import config

log = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client | None:
    """Return a Supabase client, or None when credentials aren't configured (local dev)."""
    global _client
    if _client is None and config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client


def insert_event(row: dict) -> None:
    client = get_client()
    if client is None:
        log.info("event (no db configured): %s", row)
        return
    try:
        client.table("events").insert(row).execute()
    except Exception:
        log.exception("failed to store event")


def ping() -> bool:
    """Cheapest real query we can make — counts as activity so Supabase doesn't pause the project."""
    client = get_client()
    if client is None:
        return False
    client.table("events").select("id").limit(1).execute()
    return True

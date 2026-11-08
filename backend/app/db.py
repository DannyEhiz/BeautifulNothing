"""Tiny async client for Supabase's REST API (PostgREST).

Plain httpx instead of the supabase library: fewer dependencies, fully async, and it also runs
on Cloudflare Python Workers.
"""

import logging

import httpx

from . import config

log = logging.getLogger(__name__)


class NotConfigured(RuntimeError):
    pass


class DBError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def configured() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)


def _headers(extra: dict | None = None) -> dict:
    key = config.SUPABASE_SERVICE_KEY
    headers = {"apikey": key, "Content-Type": "application/json"}
    # Legacy service_role keys are JWTs and also go in Authorization; new sb_secret_ keys must not.
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers | (extra or {})


async def _request(method: str, path: str, *, params=None, json=None, prefer: str | None = None):
    if not configured():
        raise NotConfigured("Supabase is not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY)")
    url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.request(
            method, url, params=params, json=json, headers=_headers({"Prefer": prefer} if prefer else None)
        )
    if res.status_code >= 400:
        raise DBError(res.status_code, res.text[:500])
    return res.json() if res.content else None


def _filters(where: dict | None) -> list[tuple[str, str]]:
    return [(col, f"eq.{val}") for col, val in (where or {}).items()]


async def select(
    table: str,
    where: dict | None = None,
    *,
    columns: str = "*",
    order: str | None = None,
    desc: bool = False,
    limit: int | None = None,
) -> list[dict]:
    params = [("select", columns), *_filters(where)]
    if order:
        params.append(("order", f"{order}.{'desc' if desc else 'asc'}"))
    if limit:
        params.append(("limit", str(limit)))
    return await _request("GET", table, params=params)


async def first(table: str, where: dict) -> dict | None:
    rows = await select(table, where, limit=1)
    return rows[0] if rows else None


async def insert(table: str, row: dict) -> dict:
    rows = await _request("POST", table, json=row, prefer="return=representation")
    return rows[0]


async def upsert(table: str, rows: list[dict], on_conflict: str) -> list[dict]:
    return await _request(
        "POST", table, params=[("on_conflict", on_conflict)], json=rows,
        prefer="resolution=merge-duplicates,return=representation",
    )


async def delete(table: str, where: dict) -> None:
    await _request("DELETE", table, params=_filters(where))


async def update(table: str, patch: dict, where: dict) -> list[dict]:
    """Returns the updated rows — an empty list means no row matched `where`."""
    return await _request("PATCH", table, params=_filters(where), json=patch, prefer="return=representation")


async def rpc(fn: str, args: dict | None = None):
    return await _request("POST", f"rpc/{fn}", json=args or {})


# ───────────────────────── Helpers used across the app ─────────────────────────


async def insert_event(row: dict) -> None:
    if not configured():
        log.info("event (no db configured): %s", row)
        return
    try:
        await insert("bn_events", row)
    except Exception:
        log.exception("failed to store event")


async def ping() -> bool:
    """Cheapest real query — counts as activity so Supabase doesn't pause the project."""
    if not configured():
        return False
    await select("bn_events", columns="id", limit=1)
    return True


async def active_bank_accounts() -> list[dict]:
    return await select(
        "bn_bank_accounts",
        {"is_active": "true"},
        columns="id,bank_name,account_number,account_name,account_type",
        order="sort_order",
    )

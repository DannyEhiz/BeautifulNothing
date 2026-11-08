"""Settings the admin changes in /admin → Settings, stored in Supabase (bn_settings, bn_pickup_locations).

Saved values are written onto the `config` module, so the rest of the app keeps reading `config.X`.
The environment variables are only the starting values, used until something is saved here.
Changes apply immediately, no restart needed.
"""

import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone

from . import config, db

log = logging.getLogger(__name__)

RELOAD_EVERY_SECONDS = 60


class Invalid(ValueError):
    pass


def _phase(raw: str) -> str:
    if raw not in ("launch", "regular"):
        raise Invalid
    return raw


def _naira(raw: str) -> int:
    digits = re.sub(r"[\s,₦]|\.00$", "", raw)
    if not digits.isdigit() or not 0 < int(digits) <= 10_000_000:
        raise Invalid
    return int(digits)


def _link(raw: str) -> str:
    url = config._link(raw)
    if url and not re.fullmatch(r"https?://[\w-]+(\.[\w-]+)+(/\S*)?", url):
        raise Invalid
    return url


def _admin_emails(raw: str) -> list[str]:
    found = list(dict.fromkeys(e.lower() for e in config._emails(raw)))
    if not found:
        raise Invalid
    return found


# key → (label, parser, hint shown when the value is invalid)
FIELDS: dict[str, tuple[str, Callable, str]] = {
    "SALES_PHASE": ("Sales phase", _phase, "choose Launch or After launch."),
    "SHOWLOVE_URL": ("Show love link", _link, "paste the full Selar link (https://…), or leave it empty."),
    "EBOOK_URL": ("Ebook link", _link, "paste the full Selar link (https://…), or leave it empty."),
    "EBOOK_GIFT_DRIVE_LINK": ("Ebook gift link", _link, "paste the full Google Drive link (https://…), or leave it empty."),
    "LAUNCH_GIFT_MINIMUM": ("Show love minimum", _naira, "enter an amount in naira, e.g. 5000."),
    "EBOOK_PRICE": ("Ebook price", _naira, "enter an amount in naira, e.g. 5000."),
    "PAPERBACK_DELIVERY_PRICE": ("Paperback, delivered", _naira, "enter an amount in naira, e.g. 12000."),
    "PAPERBACK_PICKUP_PRICE": ("Paperback, pickup", _naira, "enter an amount in naira, e.g. 10000."),
    "ADMIN_EMAILS": ("Notification emails", _admin_emails, "enter at least one valid email address."),
}


def _as_text(value) -> str:
    return ", ".join(value) if isinstance(value, list) else str(value)


def current() -> dict[str, str]:
    """Current values as text, for filling the settings form."""
    return {key: _as_text(getattr(config, key)) for key in FIELDS}


def pickup_names() -> str:
    """Short pickup area(s) for sentences like "…if you pick it up in Opebi, Ikeja"."""
    names = [loc["name"] for loc in config.PICKUP_LOCATIONS]
    if not names:
        return "Lagos"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]


_loaded_at = 0.0


async def load() -> None:
    global _loaded_at
    _loaded_at = time.monotonic()  # set first, so a broken database isn't retried on every request
    if not db.configured():
        return
    try:
        rows = await db.select("bn_settings")
        locations = await db.select("bn_pickup_locations", {"is_active": "true"}, order="sort_order")
    except Exception as e:
        log.warning("Couldn't load settings from Supabase, using the environment values (run supabase/schema.sql?): %s", e)
        return
    for row in rows:
        field = FIELDS.get(row["key"])
        if not field:
            continue
        try:
            setattr(config, row["key"], field[1](row["value"]))
        except Invalid:
            log.warning("Ignoring invalid saved setting %s=%r", row["key"], row["value"])
    config.PICKUP_LOCATIONS = [{"name": loc["name"], "address": loc["address"]} for loc in locations]


async def refresh_if_stale() -> None:
    if time.monotonic() - _loaded_at > RELOAD_EVERY_SECONDS:
        await load()


async def save(form: dict) -> str | None:
    """Validate and store the submitted settings. Returns an error message, or None when saved."""
    parsed = {}
    for key, (label, parse, hint) in FIELDS.items():
        if key in form:
            try:
                parsed[key] = parse((form[key] or "").strip())
            except Invalid:
                return f"{label}: {hint}"
    now = datetime.now(timezone.utc).isoformat()
    await db.upsert(
        "bn_settings", [{"key": k, "value": _as_text(v), "updated_at": now} for k, v in parsed.items()], "key"
    )
    for key, value in parsed.items():
        setattr(config, key, value)
    log.info("Settings saved: %s", ", ".join(f"{k}={_as_text(v)}" for k, v in parsed.items()))
    return None

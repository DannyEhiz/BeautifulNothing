"""Jinja2 setup shared by the public site and the admin pages."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from . import config, orders

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=BASE / "templates")

LAGOS = timezone(timedelta(hours=1))  # West Africa Time, no daylight saving


def naira(n) -> str:
    return f"₦{int(n or 0):,}"


def fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(LAGOS)
    return f"{dt.day} {dt:%b, %H:%M}"


def torn_path(seed: int, w: int = 1440, h: int = 48) -> str:
    """A ripped-paper edge, like the torn strip on the book cover (same shape on every render)."""
    s = seed

    def rnd() -> float:
        nonlocal s
        s = (s * 9301 + 49297) % 233280
        return s / 233280

    d = f"M0 {h} L0 {h * 0.55:.1f}"
    x = 0.0
    while x < w:
        d += f" L{x:.1f} {h * 0.18 + rnd() * h * 0.62:.1f}"
        x += 10 + rnd() * 26
    return f"{d} L{w} {h * 0.5:.1f} L{w} {h} Z"


env = templates.env
env.filters["naira"] = naira
env.filters["date"] = fmt_date
env.globals.update(
    cfg=config,
    torn_path=torn_path,
    STATUS_LABEL=orders.STATUS_LABEL,
    year=lambda: datetime.now(LAGOS).year,
)


def render(request: Request, name: str, status_code: int = 200, **ctx):
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)

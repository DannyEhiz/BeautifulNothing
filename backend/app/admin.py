"""Admin pages (/admin). Signed, HTTP-only session cookie; SameSite=Lax blocks cross-site form posts."""

import asyncio
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from . import config, db, emails, orders, settings, tokens
from .web import LAGOS, render

router = APIRouter(prefix="/admin")
COOKIE = "bn_admin"

FILTERS = [
    ("all", "All", None),
    ("action", "Needs action", {"payment_submitted"}),
    ("awaiting", "Awaiting payment", {"pending_payment", "rejected"}),
    ("supply", "To supply", {"acknowledged"}),
    ("transit", "Out / ready", {"dispatched", "ready_for_pickup"}),
    ("done", "Completed", {"delivered", "picked_up"}),
    ("cancelled", "Cancelled", {"cancelled"}),
]

ACTION_LABEL = {
    "acknowledged": "Acknowledge payment",
    "dispatched": "Mark out for delivery",
    "ready_for_pickup": "Mark ready for pickup",
    "delivered": "Mark delivered",
    "picked_up": "Mark picked up",
    "rejected": "Payment not found",
    "cancelled": "Cancel order",
}
BACKWARD = {"rejected", "cancelled"}

NOTICES = {
    "moved": "Order updated. The buyer has been emailed.",
    "thanked": "Thank-you email sent.",
    "dismissed": "Supporter dismissed.",
    "bank_added": "Bank account added.",
    "bank_saved": "Bank account updated.",
    "settings_saved": "Settings saved. The site is using them now.",
    "pickup_added": "Pickup location added.",
    "pickup_saved": "Pickup location updated.",
    "pickup_removed": "Pickup location removed.",
}


def _see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _is_admin(request: Request) -> bool:
    token = request.cookies.get(COOKIE, "")
    return bool(token) and tokens.check_admin_token(token)


def _to_login(request: Request) -> RedirectResponse:
    return _see_other(f"/admin/login?next={quote(request.url.path)}")


async def _form(request: Request) -> dict:
    return {k: v for k, v in (await request.form()).items() if isinstance(v, str)}


async def _summary() -> dict:
    return await db.rpc("bn_dashboard_summary") or {}


async def _page(request: Request, name: str, tab: str, summary: dict | None = None, **ctx):
    summary = summary if summary is not None else await _summary()
    counts = {
        "to_confirm": (summary.get("orders") or {}).get("payment_submitted", 0),
        "new_supporters": (summary.get("supporters") or {}).get("new", 0),
    }
    notice = NOTICES.get(request.query_params.get("n", ""))
    return render(request, name, tab=tab, counts=counts, notice=notice, summary=summary, **ctx)


# ───────────────────────── Sign in / out ─────────────────────────


def _safe_next(url: str | None) -> str:
    return url if url and url.startswith("/admin") and not url.startswith("//") else "/admin"


@router.get("/login")
async def login_page(request: Request, next: str = "/admin"):
    if _is_admin(request):
        return _see_other(_safe_next(next))
    return render(request, "admin/login.html", next=_safe_next(next))


@router.post("/login")
async def login(request: Request):
    data = await _form(request)
    nxt = _safe_next(data.get("next"))
    if not config.ADMIN_PASSWORD:
        return render(request, "admin/login.html", status_code=503, next=nxt, error_msg="ADMIN_PASSWORD is not set on the server.")
    if not secrets.compare_digest(data.get("password", "").encode(), config.ADMIN_PASSWORD.encode()):
        await asyncio.sleep(1)  # slow down guessing
        return render(request, "admin/login.html", status_code=401, next=nxt, error_msg="Wrong password.")
    res = _see_other(nxt)
    res.set_cookie(
        COOKIE, tokens.make_admin_token(), max_age=tokens.ADMIN_SESSION_MAX_AGE,
        httponly=True, samesite="lax", secure=config.SECURE_COOKIES, path="/",
    )
    return res


@router.post("/logout")
async def logout():
    res = _see_other("/admin/login")
    res.delete_cookie(COOKIE, path="/")
    return res


# ───────────────────────── Overview ─────────────────────────


def _last_30_days(daily: list[dict]) -> list[dict]:
    by_day = {d["day"]: d["visits"] for d in daily}
    today = datetime.now(timezone.utc).astimezone(LAGOS).date()
    out = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        out.append({"label": f"{day.day} {day:%b}", "n": by_day.get(day.isoformat(), 0)})
    return out


@router.get("")
async def overview(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    summary = await _summary()
    return await _page(
        request, "admin/overview.html", "overview", summary=summary,
        days=_last_30_days(summary.get("daily_visits") or []),
    )


# ───────────────────────── Orders ─────────────────────────


@router.get("/orders")
async def list_orders(request: Request, filter: str = "all"):
    if not _is_admin(request):
        return _to_login(request)
    rows = await db.select("bn_orders", order="created_at", desc=True, limit=500)
    statuses = dict((k, s) for k, _, s in FILTERS)
    if filter not in statuses:
        filter = "all"
    shown = [o for o in rows if statuses[filter] is None or o["status"] in statuses[filter]]
    counts = [(k, label, sum(1 for o in rows if s is None or o["status"] in s)) for k, label, s in FILTERS]
    return await _page(request, "admin/orders.html", "orders", orders=shown, filters=counts, filter=filter)


async def _order_page(request: Request, order: dict, **ctx):
    history = await db.select("bn_order_history", {"order_id": order["id"]}, order="created_at")
    nxt = [s for s in orders.allowed_next(order) if s in ACTION_LABEL]
    nxt.sort(key=lambda s: s in BACKWARD)  # forward steps first
    actions = [(s, ACTION_LABEL[s], s in BACKWARD) for s in nxt]
    phone = re.sub(r"\D", "", order["phone"])
    whatsapp = "234" + phone[1:] if phone.startswith("0") else phone
    return await _page(
        request, "admin/order.html", "orders", order=order, history=history, actions=actions, whatsapp=whatsapp, **ctx
    )


@router.get("/orders/{order_id}")
async def order_detail(request: Request, order_id: str):
    if not _is_admin(request):
        return _to_login(request)
    order = await orders.get_by_id(order_id)
    if not order:
        return _see_other("/admin/orders")
    return await _order_page(request, order)


@router.post("/orders/{order_id}/status")
async def change_status(request: Request, order_id: str, background: BackgroundTasks):
    if not _is_admin(request):
        return _to_login(request)
    order = await orders.get_by_id(order_id)
    if not order:
        return _see_other("/admin/orders")
    data = await _form(request)
    note = (data.get("note") or "").strip()[:500] or None
    try:
        await orders.transition(order, data.get("to", ""), actor="admin", note=note, defer=background.add_task)
    except (orders.TransitionError, KeyError):
        return await _order_page(request, order, error_msg="That step isn't possible for this order right now.")
    return _see_other(f"/admin/orders/{order_id}?n=moved")


# ───────────────────────── Supporters ─────────────────────────


@router.get("/supporters")
async def supporters(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    rows = await db.select("bn_supporters", order="created_at", desc=True, limit=1000)
    return await _page(request, "admin/supporters.html", "supporters", supporters=rows)


@router.post("/supporters/{supporter_id}/{action}")
async def supporter_action(request: Request, supporter_id: int, action: str, background: BackgroundTasks):
    if not _is_admin(request):
        return _to_login(request)
    supporter = await db.first("bn_supporters", {"id": supporter_id})
    if not supporter or action not in ("thank", "dismiss"):
        return _see_other("/admin/supporters")
    if action == "thank":
        now = datetime.now(timezone.utc).isoformat()
        rows = await db.update("bn_supporters", {"status": "thanked", "thanked_at": now}, {"id": supporter_id})
        background.add_task(emails.supporter_thanks, rows[0])
        return _see_other("/admin/supporters?n=thanked")
    await db.update("bn_supporters", {"status": "dismissed"}, {"id": supporter_id})
    return _see_other("/admin/supporters?n=dismissed")


# ───────────────────────── Waitlist ─────────────────────────


@router.get("/waitlist")
async def waitlist(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    rows = await db.select("bn_waitlist", order="created_at", desc=True, limit=1000)
    return await _page(request, "admin/waitlist.html", "waitlist", waitlist=rows)


# ───────────────────────── Guide ─────────────────────────


@router.get("/guide")
async def guide(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    return await _page(request, "admin/guide.html", "guide")


# ───────────────────────── Bank accounts ─────────────────────────


async def _banks_page(request: Request, **ctx):
    rows = await db.select("bn_bank_accounts", order="sort_order")
    return await _page(request, "admin/banks.html", "banks", banks=rows, **ctx)


@router.get("/banks")
async def banks(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    return await _banks_page(request)


@router.post("/banks")
async def add_bank(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    data = {k: (v or "").strip() for k, v in (await _form(request)).items()}
    bank, number, holder = data.get("bank_name", ""), data.get("account_number", ""), data.get("account_name", "")
    if len(bank) < 2 or not re.fullmatch(r"\d{6,20}", number) or len(holder) < 2:
        return await _banks_page(request, error_msg="Please fill in the bank, a valid account number (digits only) and the account name.")
    existing = await db.select("bn_bank_accounts", columns="id")
    try:
        await db.insert(
            "bn_bank_accounts",
            {"bank_name": bank[:80], "account_number": number, "account_name": holder[:120],
             "account_type": (data.get("account_type") or None), "sort_order": len(existing) + 1},
        )
    except db.DBError as e:
        if e.status == 409:
            return await _banks_page(request, error_msg="That account is already on the list.")
        raise
    return _see_other("/admin/banks?n=bank_added")


@router.post("/banks/{bank_id}/toggle")
async def toggle_bank(request: Request, bank_id: int):
    if not _is_admin(request):
        return _to_login(request)
    bank = await db.first("bn_bank_accounts", {"id": bank_id})
    if bank:
        await db.update("bn_bank_accounts", {"is_active": not bank["is_active"]}, {"id": bank_id})
    return _see_other("/admin/banks?n=bank_saved")


# ───────────────────────── Settings (prices, sales phase, links, pickup locations) ─────────────────────────


async def _settings_page(request: Request, status_code: int = 200, form: dict | None = None, **ctx):
    locations = await db.select("bn_pickup_locations", order="sort_order")
    page = await _page(
        request, "admin/settings.html", "settings", values=form or settings.current(), locations=locations, **ctx
    )
    page.status_code = status_code
    return page


@router.get("/settings")
async def settings_page(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    return await _settings_page(request)


@router.post("/settings")
async def save_settings(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    data = await _form(request)
    error = await settings.save(data)
    if error:
        return await _settings_page(request, 422, form={**settings.current(), **data}, error_msg=error)
    return _see_other("/admin/settings?n=settings_saved")


@router.post("/settings/pickup")
async def add_pickup(request: Request):
    if not _is_admin(request):
        return _to_login(request)
    data = {k: (v or "").strip() for k, v in (await _form(request)).items()}
    name, address = data.get("name", ""), data.get("address", "")
    if len(name) < 2 or len(address) < 5:
        return await _settings_page(request, 422, error_msg="Please give the pickup location a short name and its full address.")
    existing = await db.select("bn_pickup_locations", columns="id")
    await db.insert("bn_pickup_locations", {"name": name[:80], "address": address[:300], "sort_order": len(existing) + 1})
    await settings.load()
    return _see_other("/admin/settings?n=pickup_added#pickup")


@router.post("/settings/pickup/{location_id}/{action}")
async def pickup_action(request: Request, location_id: int, action: str):
    if not _is_admin(request):
        return _to_login(request)
    location = await db.first("bn_pickup_locations", {"id": location_id})
    if location and action == "toggle":
        await db.update("bn_pickup_locations", {"is_active": not location["is_active"]}, {"id": location_id})
    elif location and action == "delete":
        await db.delete("bn_pickup_locations", {"id": location_id})
    else:
        return _see_other("/admin/settings#pickup")
    await settings.load()
    return _see_other(f"/admin/settings?n={'pickup_saved' if action == 'toggle' else 'pickup_removed'}#pickup")

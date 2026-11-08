"""Public pages: landing, show love, paperback ordering, order status, and the admin email's acknowledge link."""

import asyncio
import logging
import re
import secrets
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError

from . import config, content, db, emails, orders, tokens
from .web import render

log = logging.getLogger(__name__)
router = APIRouter()

FIELD_NAMES = {
    "name": "Name",
    "email": "Email",
    "phone": "Phone",
    "address": "Delivery address",
    "quantity": "Copies",
    "location": "City / State",
    "payer_name": "Name on the account",
    "payer_bank": "Bank",
}


def _is_bot(data: dict, form: str) -> bool:
    # Hidden "bn_check" field: invisible to people, but simple spam bots fill every input.
    if data.get("bn_check"):
        log.warning("%s form: hidden spam-check field was filled, treating as a bot", form)
        return True
    return False


def _clean(s: str | None) -> str | None:
    s = (s or "").strip()
    return s or None


def _see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


async def _form(request: Request) -> dict:
    return {k: v for k, v in (await request.form()).items() if isinstance(v, str)}


def _validate(model: type[BaseModel], data: dict):
    """Returns (instance, None) or (None, friendly message)."""
    try:
        return model(**data), None
    except ValidationError as e:
        err = e.errors()[0]
        field = FIELD_NAMES.get(str(err["loc"][-1]) if err["loc"] else "", "")
        if err["type"].startswith("value_error") and "email" in str(err["loc"]):
            return None, "Please enter a valid email address."
        if err["type"] in ("string_too_short", "missing"):
            return None, f"{field or 'A required field'} is missing or too short."
        return None, f"{field + ': ' if field else ''}{err['msg']}"


def _landing(request: Request, status_code: int = 200, **ctx):
    return render(
        request,
        "landing.html",
        status_code=status_code,
        stories=content.STORIES,
        wall=content.WALL,
        timeline=content.TIMELINE,
        love_form=ctx.pop("love_form", {}),
        **ctx,
    )


# ───────────────────────── Landing + Show love ─────────────────────────


@router.get("/")
async def landing(request: Request, love: str | None = None):
    return _landing(request, love_state="saved" if love == "saved" else None)


class SupporterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    visitor_id: str | None = Field(default=None, max_length=64)


@router.post("/show-love")
async def show_love(request: Request):
    data = await _form(request)
    if _is_bot(data, "show love"):
        return _see_other("/")
    body, error = _validate(SupporterIn, data)
    if error:
        return _landing(request, 422, love_state="error", love_error=error, love_form=data)
    await db.insert(
        "bn_supporters",
        {"name": body.name.strip(), "email": body.email.lower(), "visitor_id": _clean(body.visitor_id)},
    )
    if not config.SHOWLOVE_URL:
        log.warning("show love: supporter saved, but SHOWLOVE_URL is not set, so staying on the site")
        return _see_other("/?love=saved#get")
    log.info("show love: supporter saved, sending them to %s", config.SHOWLOVE_URL)
    return _see_other(config.SHOWLOVE_URL)


# ───────────────────────── Thank-you page (Selar redirects here after payment) ─────────────────────────


@router.get("/thank-you")
async def thank_you(request: Request, source: str = Query("", alias="from")):
    return render(request, "thank_you.html", source=source if source in ("showlove", "ebook") else "")


# ───────────────────────── Paperback orders ─────────────────────────


class OrderIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    fulfilment: Literal["delivery", "pickup"]
    address: str | None = Field(default=None, max_length=300)
    area: str | None = Field(default=None, max_length=120)
    quantity: int = Field(ge=1, le=20)
    note: str | None = Field(default=None, max_length=500)


@router.get("/order")
async def order_form(request: Request):
    return render(request, "order.html", form={"fulfilment": "delivery", "quantity": 1})


@router.post("/order")
async def place_order(request: Request, background: BackgroundTasks):
    data = await _form(request)
    if _is_bot(data, "order"):
        return _see_other("/order")
    body, error = _validate(OrderIn, data)
    if not error and body.fulfilment == "delivery" and not _clean(body.address):
        error = "Please enter your delivery address."
    if error:
        return render(request, "order.html", status_code=422, form=data, error_msg=error)

    price = orders.unit_price(body.fulfilment)
    delivery = body.fulfilment == "delivery"
    order = await db.insert(
        "bn_orders",
        {
            "access_token": secrets.token_urlsafe(24),
            "name": body.name.strip(),
            "email": body.email.lower(),
            "phone": body.phone.strip(),
            "fulfilment": body.fulfilment,
            "address": _clean(body.address) if delivery else None,
            "area": _clean(body.area) if delivery else None,
            "quantity": body.quantity,
            "unit_price": price,
            "total": price * body.quantity,
            "note": _clean(body.note),
        },
    )
    await db.insert(
        "bn_order_history",
        {"order_id": order["id"], "from_status": None, "to_status": "pending_payment", "actor": "buyer"},
    )
    banks = await db.active_bank_accounts()
    background.add_task(emails.buyer_order_placed, order, banks)
    background.add_task(emails.admin_new_order, order)
    return _see_other(f"/order/{order['code']}?t={order['access_token']}")


class WaitlistIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    location: str = Field(min_length=2, max_length=120)
    quantity: int = Field(default=1, ge=1, le=20)


@router.get("/order/waitlist")
async def waitlist_form(request: Request):
    return render(request, "waitlist.html", form={})


@router.post("/order/waitlist")
async def join_waitlist(request: Request, background: BackgroundTasks):
    data = await _form(request)
    if _is_bot(data, "waitlist"):
        return render(request, "waitlist.html", done=True, form={})
    body, error = _validate(WaitlistIn, data)
    if error:
        return render(request, "waitlist.html", status_code=422, form=data, error_msg=error)
    entry = {
        "name": body.name.strip(),
        "email": body.email.lower(),
        "phone": _clean(body.phone),
        "location": body.location.strip(),
        "quantity": body.quantity,
    }
    await db.insert("bn_waitlist", entry)
    background.add_task(emails.admin_waitlist, entry)
    return render(request, "waitlist.html", done=True, form={})


@router.get("/order/find")
async def find_order_form(request: Request):
    return render(request, "order_find.html", form={})


@router.post("/order/find")
async def find_order(request: Request):
    data = await _form(request)
    code = re.sub(r"\s", "", data.get("code", "")).upper()
    if code and not code.startswith("BN-"):
        code = "BN-" + code.removeprefix("BN")  # accept "BN0007" or "0007"
    email = data.get("email", "").strip().lower()
    order = await orders.get_by_code(code) if re.fullmatch(r"BN-\d{1,8}", code) and email else None
    if not order or not secrets.compare_digest(order["email"].lower(), email):
        await asyncio.sleep(1)  # slow down guessing
        return render(
            request, "order_find.html", status_code=404, form=data,
            error_msg="We couldn't find an order with that number and email. Please check both and try again.",
        )
    return _see_other(f"/order/{order['code']}?t={order['access_token']}")


async def _buyer_order(code: str, t: str) -> dict | None:
    order = await orders.get_by_code(code)
    # Same answer for "no such order" and "wrong token", so order codes can't be probed.
    if not order or not t or not secrets.compare_digest(order["access_token"], t):
        return None
    return order


def _not_found(request: Request):
    return render(
        request,
        "message.html",
        status_code=404,
        heading="Order not found",
        text="We couldn't find that order. You can look it up with your order number and email.",
        link="/order/find",
        link_label="Find my order",
    )


async def _status_page(request: Request, order: dict, status_code: int = 200, **ctx):
    banks = await db.active_bank_accounts() if order["status"] in orders.AWAITING_PAYMENT else []
    return render(
        request, "order_status.html", status_code=status_code, order=order, token=order["access_token"],
        banks=banks, form=ctx.pop("form", {}), **ctx,
    )


@router.get("/order/{code}")
async def order_status(request: Request, code: str, t: str = ""):
    order = await _buyer_order(code, t)
    if not order:
        return _not_found(request)
    return await _status_page(request, order)


class PaidIn(BaseModel):
    payer_name: str = Field(min_length=2, max_length=120)
    payer_bank: str = Field(min_length=2, max_length=80)
    payer_reference: str | None = Field(default=None, max_length=80)


@router.post("/order/{code}/paid")
async def report_payment(request: Request, code: str, background: BackgroundTasks, t: str = ""):
    order = await _buyer_order(code, t)
    if not order:
        return _not_found(request)
    data = await _form(request)
    body, error = _validate(PaidIn, data)
    if error:
        return await _status_page(request, order, 422, form=data, error_msg=error)
    if order["status"] in orders.AWAITING_PAYMENT:
        try:
            await orders.transition(
                order,
                "payment_submitted",
                actor="buyer",
                defer=background.add_task,
                extra={
                    "payer_name": body.payer_name.strip(),
                    "payer_bank": body.payer_bank.strip(),
                    "payer_reference": _clean(body.payer_reference),
                },
            )
        except orders.TransitionError as e:
            return await _status_page(request, order, 409, form=data, error_msg=str(e))
    return _see_other(f"/order/{order['code']}?t={order['access_token']}")


# ───────────────────────── Acknowledge from the admin email ─────────────────────────
# GET only shows the order; the POST changes it, so link scanners that pre-open email
# links can't acknowledge anything by accident.


async def _order_from_ack_token(token: str) -> dict | None:
    data = tokens.read_action_token(token)
    if not data or data.get("action") != "acknowledge":
        return None
    return await orders.get_by_id(data["order"])


def _bad_link(request: Request):
    return render(
        request,
        "message.html",
        status_code=400,
        heading="Link problem",
        text="This acknowledge link is invalid or has expired. Please use the admin page.",
        link="/admin",
        link_label="Open admin",
    )


def _ack_page(request: Request, order: dict, token: str, **ctx):
    return render(
        request, "ack.html", order=order, token=token,
        can_acknowledge="acknowledged" in orders.allowed_next(order), **ctx,
    )


@router.get("/ack")
async def ack_preview(request: Request, token: str = ""):
    order = await _order_from_ack_token(token)
    if not order:
        return _bad_link(request)
    return _ack_page(request, order, token)


@router.post("/ack")
async def ack_confirm(request: Request, background: BackgroundTasks):
    token = (await _form(request)).get("token", "")
    order = await _order_from_ack_token(token)
    if not order:
        return _bad_link(request)
    if order["status"] in orders.CONFIRMED:
        return _ack_page(request, order, token)
    try:
        order = await orders.transition(order, "acknowledged", actor="admin-email", defer=background.add_task)
    except orders.TransitionError as e:
        return _ack_page(request, order, token, error_msg=str(e))
    return _ack_page(request, order, token, result="done")

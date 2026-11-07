"""Transactional emails, sent through Brevo's HTTP API (Render's free tier blocks outbound SMTP)."""

import logging
from html import escape

import httpx

from . import config

log = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def naira(n: int) -> str:
    return f"₦{n:,}"


async def send(to: list[str], subject: str, html: str) -> None:
    to = [t for t in to if t]
    if not to:
        return
    if not (config.BREVO_API_KEY and config.MAIL_FROM_EMAIL):
        log.warning("EMAIL NOT SENT (BREVO_API_KEY or MAIL_FROM_EMAIL missing) to: %s | subject: %s", ", ".join(to), subject)
        return
    payload = {
        "sender": {"email": config.MAIL_FROM_EMAIL, "name": config.MAIL_FROM_NAME},
        "to": [{"email": t} for t in to],
        "subject": subject,
        "htmlContent": html,
    }
    if config.MAIL_REPLY_TO:
        payload["replyTo"] = {"email": config.MAIL_REPLY_TO, "name": config.MAIL_FROM_NAME}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                BREVO_URL, headers={"api-key": config.BREVO_API_KEY, "accept": "application/json"}, json=payload
            )
    except Exception:
        log.exception("EMAIL FAILED (could not reach Brevo) %r to %s", subject, to)
        return
    if res.status_code >= 400:
        # Brevo explains the problem in the body: unverified sender, wrong key type, account not activated...
        log.error("EMAIL FAILED (Brevo said %s): %s | subject: %r to %s", res.status_code, res.text[:500], subject, to)
    else:
        log.info("email sent: %r to %s", subject, to)


# ───────────────────────── Layout ─────────────────────────


def _layout(heading: str, body: str) -> str:
    return f"""<!doctype html><html><body style="margin:0;background:#ecebe6;font-family:Georgia,'Times New Roman',serif;color:#161616">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ecebe6;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:14px;overflow:hidden">
  <tr><td style="background:#121212;padding:26px 28px">
    <div style="font-family:Georgia,serif;font-size:22px;letter-spacing:3px;color:#efede6;text-transform:uppercase">Beautiful Nothing</div>
    <div style="font-style:italic;color:#d7262f;font-size:15px;margin-top:2px">Stories by Oladimeji Ramon</div>
  </td></tr>
  <tr><td style="padding:28px 28px 8px">
    <h1 style="margin:0 0 16px;font-size:24px;line-height:1.25;font-weight:normal">{heading}</h1>
    <div style="font-size:16px;line-height:1.6;color:#333">{body}</div>
  </td></tr>
  <tr><td style="padding:18px 28px 28px;font-family:Arial,sans-serif;font-size:12px;color:#888">
    Beautiful Nothing · Stories by Oladimeji Ramon
  </td></tr>
</table>
</td></tr></table></body></html>"""


def _button(url: str, label: str, color: str = "#d7262f") -> str:
    return (
        f'<p style="margin:24px 0"><a href="{escape(url)}" style="display:inline-block;background:{color};color:#fff;'
        f'font-family:Arial,sans-serif;font-size:15px;font-weight:bold;text-decoration:none;padding:13px 24px;'
        f'border-radius:999px">{escape(label)}</a></p>'
    )


def _rows(pairs: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<tr><td style="padding:7px 12px 7px 0;color:#777;font-family:Arial,sans-serif;font-size:13px;white-space:nowrap;vertical-align:top">{escape(k)}</td>'
        f'<td style="padding:7px 0;font-size:15px">{escape(v)}</td></tr>'
        for k, v in pairs
        if v
    )
    return f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 4px">{cells}</table>'


def _order_rows(order: dict) -> str:
    how = "Delivery (Lagos)" if order["fulfilment"] == "delivery" else "Pickup at the store"
    pairs = [
        ("Order", order["code"]),
        ("Copies", str(order["quantity"])),
        ("How", how),
        ("Total", naira(order["total"])),
    ]
    if order["fulfilment"] == "delivery":
        pairs.append(("Deliver to", ", ".join(p for p in (order.get("address"), order.get("area")) if p)))
    return _rows(pairs)


def _bank_block(banks: list[dict], amount: int, code: str) -> str:
    accounts = "".join(
        f'<div style="border:1px solid #e3e1da;border-radius:10px;padding:12px 14px;margin:8px 0">'
        f'<div style="font-family:Arial,sans-serif;font-size:12px;color:#777;text-transform:uppercase;letter-spacing:1px">{escape(b["bank_name"])}</div>'
        f'<div style="font-size:20px;letter-spacing:1px;margin:2px 0">{escape(b["account_number"])}</div>'
        f'<div style="font-size:14px;color:#555">{escape(b["account_name"])}</div></div>'
        for b in banks
    )
    return (
        f"<p>Please transfer <strong>{naira(amount)}</strong> to any of these accounts and use "
        f"<strong>{escape(code)}</strong> as the transfer narration/description:</p>{accounts}"
    )


def order_link(order: dict) -> str:
    return f"{config.SITE_URL}/order/{order['code']}?t={order['access_token']}"


# ───────────────────────── Buyer emails ─────────────────────────


async def buyer_order_placed(order: dict, banks: list[dict]) -> None:
    body = (
        f"<p>Hi {escape(order['name'])}, thank you for ordering <em>Beautiful Nothing</em>.</p>"
        f"{_order_rows(order)}"
        f"{_bank_block(banks, order['total'], order['code'])}"
        f"<p>Once you've paid, tap the button below and tell us which account you paid from, so we can "
        f"match your transfer quickly.</p>"
        f"{_button(order_link(order), 'I have paid')}"
    )
    await send([order["email"]], f"Your order {order['code']} — payment details", _layout("Order received", body))


BUYER_STATUS_COPY = {
    "acknowledged": (
        "Payment confirmed",
        "We've confirmed your payment for order {code}. Your copy is being prepared and we'll let you know as soon as it's on its way.",
    ),
    "rejected": (
        "We couldn't confirm your payment",
        "We couldn't find a payment matching order {code}. Please check that the transfer went through, then confirm your payment details again, or reply to this email.",
    ),
    "dispatched": (
        "Your book is on its way",
        "Order {code} is out for delivery. Please keep your phone close — the rider may call before arriving.",
    ),
    "ready_for_pickup": (
        "Ready for pickup",
        "Order {code} is ready. Come by the store with your order number to collect your copy:<br><strong>{store}</strong>",
    ),
    "delivered": ("Delivered — enjoy the stories", "Order {code} has been delivered. Thank you for reading <em>Beautiful Nothing</em>."),
    "picked_up": ("Enjoy the stories", "Thanks for picking up order {code}. We hope <em>Beautiful Nothing</em> stays with you."),
    "cancelled": ("Order cancelled", "Order {code} has been cancelled. If this is unexpected, just reply to this email."),
}


async def buyer_status_changed(order: dict, status: str) -> None:
    copy = BUYER_STATUS_COPY.get(status)
    if not copy:
        return
    heading, text = copy
    body = f"<p>Hi {escape(order['name'])},</p><p>{text.format(code=escape(order['code']), store=escape(config.PICKUP_STORE))}</p>"
    body += _order_rows(order)
    if status == "rejected":
        body += _button(order_link(order), "Confirm payment again")
    else:
        body += _button(order_link(order), "View your order", color="#121212")
    await send([order["email"]], f"{heading} — {order['code']}", _layout(heading, body))


# ───────────────────────── Admin emails ─────────────────────────


async def admin_new_order(order: dict) -> None:
    body = (
        f"<p>Someone wants the paperback. Payment hasn't been made yet; you'll get another email with an "
        f"<strong>Acknowledge</strong> button when they say they've paid.</p>"
        f"{_rows([('Name', order['name']), ('Phone', order['phone']), ('Email', order['email'])])}"
        f"{_order_rows(order)}"
        f"{_button(config.SITE_URL + '/admin', 'Open admin', color='#121212')}"
    )
    await send(config.ADMIN_EMAILS, f"New paperback order {order['code']} — {naira(order['total'])}", _layout("New order", body))


async def admin_payment_submitted(order: dict, ack_url: str) -> None:
    body = (
        f"<p><strong>{escape(order['name'])}</strong> says they've paid for order <strong>{escape(order['code'])}</strong>. "
        f"Check your bank for this transfer before acknowledging:</p>"
        + _rows([
            ("Amount", naira(order["total"])),
            ("From (name)", order.get("payer_name") or ""),
            ("From (bank)", order.get("payer_bank") or ""),
            ("Reference", order.get("payer_reference") or ""),
            ("Narration", order["code"]),
        ])
        + f"<p style=\"margin-top:18px\">Buyer: {escape(order['phone'])} · {escape(order['email'])}</p>"
        f"{_order_rows(order)}"
        f"{_button(ack_url, 'Acknowledge order')}"
        f'<p style="font-size:13px;color:#777">The button opens a confirmation page. Nothing changes until you confirm there.</p>'
    )
    await send(config.ADMIN_EMAILS, f"Payment to confirm: {order['code']}, {naira(order['total'])}", _layout("Payment to confirm", body))


async def admin_waitlist(entry: dict) -> None:
    body = (
        "<p>Someone outside Lagos wants the paperback delivered:</p>"
        + _rows([("Name", entry["name"]), ("Email", entry["email"]), ("Phone", entry.get("phone") or ""),
                 ("Location", entry["location"]), ("Copies", str(entry["quantity"]))])
    )
    await send(config.ADMIN_EMAILS, f"Delivery request from outside Lagos — {entry['location']}", _layout("Waitlist", body))


# ───────────────────────── Supporters ─────────────────────────


async def supporter_thanks(supporter: dict) -> None:
    book = (
        f"<p>As a thank-you, here is your copy of the ebook:</p>{_button(config.EBOOK_GIFT_DRIVE_LINK, 'Download your ebook')}"
        f'<p style="font-size:13px;color:#777">The link opens the book on Google Drive, where you can read it or download it.</p>'
        if config.EBOOK_GIFT_DRIVE_LINK
        else "<p>Your copy of the ebook will follow shortly.</p>"
    )
    body = (
        f"<p>Dear {escape(supporter['name'])},</p>"
        f"<p>Thank you for showing love to <em>Beautiful Nothing</em>. Your gift at the launch means more "
        f"than I can put into words, and it helps these stories find their readers.</p>{book}"
        f"<p>With gratitude,<br>Oladimeji Ramon</p>"
    )
    await send([supporter["email"]], "Thank you for the love ❤", _layout("Thank you", body))

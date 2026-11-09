"""Paperback order lifecycle.

    pending_payment ──► payment_submitted ──► acknowledged ──► dispatched ──────► delivered      (delivery)
           │                   │    ▲               │      └─► ready_for_pickup ─► picked_up      (pickup)
           │                   ▼    │               │
           │                rejected                │
           └──────────────► cancelled ◄─────────────┘

"payment_submitted" = the buyer told us which account they paid from. The admin checks the bank
for that transfer, then acknowledges. The admin may also acknowledge straight from
pending_payment/rejected (they saw the money arrive before the buyer said anything).
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from app import config, db, emails

log = logging.getLogger(__name__)

TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"payment_submitted", "acknowledged", "cancelled"},
    "payment_submitted": {"acknowledged", "rejected", "cancelled"},
    "rejected": {"payment_submitted", "acknowledged", "cancelled"},
    "acknowledged": {"dispatched", "ready_for_pickup", "cancelled"},
    "dispatched": {"delivered"},
    "ready_for_pickup": {"picked_up"},
}
DELIVERY_ONLY = {"dispatched", "delivered"}
PICKUP_ONLY = {"ready_for_pickup", "picked_up"}
CONFIRMED = {"acknowledged", "dispatched", "ready_for_pickup", "delivered", "picked_up"}
AWAITING_PAYMENT = {"pending_payment", "rejected"}

STATUS_LABEL = {
    "pending_payment": "Awaiting payment",
    "payment_submitted": "Payment to confirm",
    "rejected": "Payment not found",
    "acknowledged": "Acknowledged",
    "dispatched": "Out for delivery",
    "ready_for_pickup": "Ready for pickup",
    "delivered": "Delivered",
    "picked_up": "Picked up",
    "cancelled": "Cancelled",
}

TIMESTAMP_FOR = {
    "payment_submitted": "payment_reported_at",
    "acknowledged": "acknowledged_at",
    "dispatched": "dispatched_at",
    "ready_for_pickup": "dispatched_at",
    "delivered": "completed_at",
    "picked_up": "completed_at",
    "cancelled": "cancelled_at",
}


class TransitionError(ValueError):
    pass


def allowed_next(order: dict) -> list[str]:
    nxt = TRANSITIONS.get(order["status"], set())
    nxt = nxt - (PICKUP_ONLY if order["fulfilment"] == "delivery" else DELIVERY_ONLY)
    return sorted(nxt)


def unit_price(fulfilment: str) -> int:
    return config.PAPERBACK_DELIVERY_PRICE if fulfilment == "delivery" else config.PAPERBACK_PICKUP_PRICE


async def get_by_id(order_id: str) -> dict | None:
    return await db.first("bn_orders", {"id": order_id})


async def get_by_code(code: str) -> dict | None:
    return await db.first("bn_orders", {"code": code.upper()})


async def transition(
    order: dict,
    to: str,
    actor: str,
    defer: Callable,
    note: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Move an order to a new status, record history, and queue the matching email via `defer`
    (pass BackgroundTasks.add_task from a route). Returns the updated order."""
    if to not in allowed_next(order):
        raise TransitionError(f"Order {order['code']} can't go from {STATUS_LABEL[order['status']].lower()} to {STATUS_LABEL[to].lower()}")

    now = datetime.now(timezone.utc).isoformat()
    patch = {"status": to, "updated_at": now, **(extra or {})}
    if col := TIMESTAMP_FOR.get(to):
        patch[col] = now
    if note and actor != "buyer":
        patch["admin_note"] = note

    # Only update if nobody changed it in the meantime (e.g. two admins clicking at once).
    rows = await db.update("bn_orders", patch, {"id": order["id"], "status": order["status"]})
    if not rows:
        raise TransitionError(f"Order {order['code']} was just changed by someone else. Refresh and try again.")
    updated = rows[0]

    await db.insert(
        "bn_order_history",
        {"order_id": order["id"], "from_status": order["status"], "to_status": to, "actor": actor, "note": note},
    )

    if to == "payment_submitted":
        defer(emails.admin_payment_submitted, updated)
    else:
        defer(emails.buyer_status_changed, updated, to)
    return updated

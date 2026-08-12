from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import stripe

from app.core.config import get_settings
from app.models.order import Order

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

MIN_STRIPE_CHECKOUT_EXPIRE_MINUTES = 30


def money_to_minor_units(amount: Decimal) -> int:
    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def build_checkout_line_items(order: Order) -> list[dict[str, Any]]:
    line_items = [
        {
            "price_data": {
                "currency": settings.stripe_currency,
                "product_data": {
                    "name": f"{item.shrimp_name_snapshot} - {item.variant_name_snapshot}",
                },
                "unit_amount": money_to_minor_units(item.unit_price),
            },
            "quantity": item.quantity,
        }
        for item in order.items
    ]

    if order.shipping_amount > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": settings.stripe_currency,
                    "product_data": {"name": "Australia Post shipping"},
                    "unit_amount": money_to_minor_units(order.shipping_amount),
                },
                "quantity": 1,
            }
        )

    return line_items


def get_checkout_expires_at() -> int:
    # Stripe Checkout currently enforces 30 minutes as the minimum session lifetime.
    minutes = max(
        settings.stripe_checkout_expires_after_minutes,
        MIN_STRIPE_CHECKOUT_EXPIRE_MINUTES,
    )
    return int((datetime.now(UTC) + timedelta(minutes=minutes)).timestamp())


def create_order_checkout_session(
    *,
    order: Order,
    customer_email: str,
) -> stripe.checkout.Session:
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe secret key is not configured.")

    return stripe.checkout.Session.create(
        mode="payment",
        customer_email=customer_email,
        line_items=build_checkout_line_items(order),
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        expires_at=get_checkout_expires_at(),
        metadata={
            "order_id": str(order.id),
            "order_number": order.order_number,
        },
        payment_intent_data={
            "metadata": {
                "order_id": str(order.id),
                "order_number": order.order_number,
            },
        },
    )


def construct_stripe_webhook_event(
    *,
    payload: bytes,
    signature: str,
) -> stripe.Event:
    if not settings.stripe_webhook_secret:
        raise RuntimeError("Stripe webhook secret is not configured.")

    return stripe.Webhook.construct_event(
        payload,
        signature,
        settings.stripe_webhook_secret,
    )

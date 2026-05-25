from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID

import stripe

from app.config import settings

SUBSCRIPTION_TYPE_PRO = "pro"
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


class StripeConfigurationError(RuntimeError):
    pass


def _require_setting(value: str | None, name: str) -> str:
    if value:
        return value
    raise StripeConfigurationError(f"{name} is not configured")


@lru_cache
def get_stripe_client() -> stripe.StripeClient:
    return stripe.StripeClient(_require_setting(settings.stripe_secret_key, "STRIPE_SECRET_KEY"))


def construct_webhook_event(payload: bytes, signature: str | None) -> stripe.Event:
    if not signature:
        raise ValueError("Missing Stripe-Signature header")
    webhook_secret = _require_setting(settings.stripe_webhook_secret, "STRIPE_WEBHOOK_SECRET")
    return stripe.Webhook.construct_event(payload, signature, webhook_secret)


def create_customer(*, email: str, name: str | None = None) -> stripe.Customer:
    return get_stripe_client().v1.customers.create(
        params={
            "email": email,
            "name": name or email,
        }
    )


def retrieve_customer(customer_id: str) -> stripe.Customer:
    return get_stripe_client().v1.customers.retrieve(customer_id)


def create_checkout_session(
    *,
    stripe_customer_id: str,
    user_id: UUID,
    subscription_type: str = SUBSCRIPTION_TYPE_PRO,
) -> stripe.checkout.Session:
    price_id = _require_setting(settings.stripe_pro_price_id, "STRIPE_PRO_PRICE_ID")
    metadata = {
        "user_id": str(user_id),
        "subscription_type": subscription_type,
    }
    return_url = (
        f"{settings.frontend_url.rstrip('/')}/app"
        "?tab=subscription&checkout_session_id={CHECKOUT_SESSION_ID}"
    )
    return get_stripe_client().v1.checkout.sessions.create(
        params={
            "customer": stripe_customer_id,
            "line_items": [{"price": price_id, "quantity": 1}],
            "metadata": metadata,
            "mode": "subscription",
            "return_url": return_url,
            "subscription_data": {"metadata": metadata},
            "ui_mode": "embedded_page",
        }
    )


def retrieve_checkout_session(session_id: str) -> stripe.checkout.Session:
    return get_stripe_client().v1.checkout.sessions.retrieve(session_id)


def retrieve_subscription(subscription_id: str) -> stripe.Subscription:
    return get_stripe_client().v1.subscriptions.retrieve(subscription_id)


def create_portal_session(*, stripe_customer_id: str) -> stripe.billing_portal.Session:
    return get_stripe_client().v1.billing_portal.sessions.create(
        params={
            "customer": stripe_customer_id,
            "return_url": f"{settings.frontend_url.rstrip('/')}/app?tab=subscription",
        }
    )


def stripe_value(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def stripe_id(obj: Any) -> str | None:
    if isinstance(obj, str):
        return obj
    value = stripe_value(obj, "id")
    return value if isinstance(value, str) else None


def subscription_is_active(status: str | None) -> bool:
    return status in ACTIVE_SUBSCRIPTION_STATUSES

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Subscription, User
from app.services.auth import CurrentUser
from app.src.connections.stripe_connection.stripe_connection import (
    StripeConfigurationError,
    StripeSubscriptionData,
    create_checkout_session,
    create_customer,
    create_portal_session,
    construct_webhook_event,
    parse_subscription,
    retrieve_checkout_session,
    retrieve_subscription,
    stripe_id,
    stripe_value,
    subscription_is_active,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscriptionResponse(BaseModel):
    subscription_type: str | None
    active: bool
    status: str | None
    current_period_end: datetime | None


class CreateCheckoutSessionResponse(BaseModel):
    client_secret: str
    session_id: str


class CheckoutSessionStatusResponse(BaseModel):
    status: str | None
    payment_status: str | None


class BillingPortalSessionResponse(BaseModel):
    url: str


def _active_subscription(db: Session, user_id: UUID) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.active.is_(True))
        .order_by(Subscription.updated_at.desc())
    )


def _latest_subscription(db: Session, user_id: UUID) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.active.desc(), Subscription.updated_at.desc())
    )


def _subscription_response(subscription: Subscription | None) -> SubscriptionResponse:
    if subscription is None:
        return SubscriptionResponse(
            subscription_type=None,
            active=False,
            status=None,
            current_period_end=None,
        )
    return SubscriptionResponse(
        subscription_type=subscription.subscription_type,
        active=subscription.active,
        status=subscription.status,
        current_period_end=subscription.current_period_end,
    )


def _ensure_stripe_customer(user: User, db: Session) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = create_customer(email=user.email, name=user.email)
    customer_id = stripe_id(customer)
    if not customer_id:
        raise HTTPException(502, "Stripe returned a customer without an id.")

    user.stripe_customer_id = customer_id
    db.add(user)
    db.commit()
    db.refresh(user)
    return customer_id


def _user_for_subscription(db: Session, data: StripeSubscriptionData) -> User | None:
    if data.user_id:
        try:
            user = db.get(User, UUID(data.user_id))
            if user is not None:
                return user
        except ValueError:
            logger.warning("Stripe subscription has invalid user_id metadata: %s", data.user_id)

    return db.scalar(select(User).where(User.stripe_customer_id == data.customer_id))


def _sync_subscription_from_stripe(db: Session, stripe_subscription: Any) -> Subscription | None:
    data = parse_subscription(stripe_subscription)
    if data is None:
        logger.warning("Skipping incomplete Stripe subscription payload")
        return None

    user = _user_for_subscription(db, data)
    if user is None:
        logger.warning(
            "Skipping Stripe subscription %s because no app user matches customer %s",
            data.id,
            data.customer_id,
        )
        return None
    if not user.stripe_customer_id:
        user.stripe_customer_id = data.customer_id

    row = db.scalar(
        select(Subscription).where(Subscription.stripe_subscription_id == data.id)
    )
    if row is None:
        row = Subscription(stripe_subscription_id=data.id)
        db.add(row)

    row.user_id = user.id
    row.stripe_customer_id = data.customer_id
    row.subscription_type = data.subscription_type
    row.status = data.status
    row.active = subscription_is_active(data.status)
    row.stripe_price_id = data.price_id
    row.current_period_end = data.current_period_end

    db.add(user)
    db.commit()
    db.refresh(row)
    return row


def _sync_checkout_session(db: Session, checkout_session: Any) -> None:
    subscription_id = stripe_id(stripe_value(checkout_session, "subscription"))
    if not subscription_id:
        logger.info("Checkout session completed without a subscription id")
        return
    _sync_subscription_from_stripe(db, retrieve_subscription(subscription_id))


def _sync_invoice(db: Session, invoice: Any) -> None:
    subscription_id = stripe_id(stripe_value(invoice, "subscription"))
    if subscription_id:
        _sync_subscription_from_stripe(db, retrieve_subscription(subscription_id))


@router.get("/subscription/", response_model=SubscriptionResponse)
def get_subscription(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionResponse:
    return _subscription_response(_latest_subscription(db, current_user.id))


@router.post("/checkout_session/", response_model=CreateCheckoutSessionResponse)
def checkout_session(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CreateCheckoutSessionResponse:
    if _active_subscription(db, current_user.id):
        raise HTTPException(409, "User already has an active subscription.")

    try:
        stripe_customer_id = _ensure_stripe_customer(current_user, db)
        session = create_checkout_session(
            stripe_customer_id=stripe_customer_id,
            user_id=current_user.id,
        )
    except StripeConfigurationError as exc:
        raise HTTPException(500, str(exc)) from exc
    except stripe.StripeError as exc:
        logger.exception("Stripe checkout session creation failed")
        raise HTTPException(502, str(exc)) from exc

    client_secret = stripe_value(session, "client_secret")
    session_id = stripe_id(session)
    if not isinstance(client_secret, str) or not session_id:
        raise HTTPException(502, "Stripe returned an incomplete checkout session.")
    return CreateCheckoutSessionResponse(client_secret=client_secret, session_id=session_id)


@router.get("/checkout_session/{session_id}", response_model=CheckoutSessionStatusResponse)
def get_checkout_session_status(
    session_id: str,
    current_user: CurrentUser,
) -> CheckoutSessionStatusResponse:
    try:
        session = retrieve_checkout_session(session_id)
    except StripeConfigurationError as exc:
        raise HTTPException(500, str(exc)) from exc
    except stripe.StripeError as exc:
        raise HTTPException(502, str(exc)) from exc

    if stripe_id(stripe_value(session, "customer")) != current_user.stripe_customer_id:
        raise HTTPException(404, "Checkout session not found.")
    return CheckoutSessionStatusResponse(
        status=stripe_value(session, "status"),
        payment_status=stripe_value(session, "payment_status"),
    )


@router.post("/portal_session/", response_model=BillingPortalSessionResponse)
def portal_session(
    current_user: CurrentUser,
) -> BillingPortalSessionResponse:
    if not current_user.stripe_customer_id:
        raise HTTPException(409, "User does not have a Stripe customer.")
    try:
        session = create_portal_session(stripe_customer_id=current_user.stripe_customer_id)
    except StripeConfigurationError as exc:
        raise HTTPException(500, str(exc)) from exc
    except stripe.StripeError as exc:
        logger.exception("Stripe billing portal session creation failed")
        raise HTTPException(502, str(exc)) from exc

    url = stripe_value(session, "url")
    if not isinstance(url, str):
        raise HTTPException(502, "Stripe returned a billing portal session without a URL.")
    return BillingPortalSessionResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    payload = await request.body()
    try:
        event = construct_webhook_event(payload, stripe_signature)
    except StripeConfigurationError as exc:
        raise HTTPException(500, str(exc)) from exc
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid Stripe webhook signature.") from exc

    event_type = stripe_value(event, "type")
    event_data = stripe_value(event, "data")
    obj = stripe_value(event_data, "object")

    try:
        if event_type == "checkout.session.completed":
            _sync_checkout_session(db, obj)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            _sync_subscription_from_stripe(db, obj)
        elif event_type in {"invoice.paid", "invoice.payment_failed"}:
            _sync_invoice(db, obj)
        else:
            logger.debug("Ignoring Stripe event type=%s", event_type)
    except stripe.StripeError as exc:
        logger.exception("Stripe webhook sync failed for event type=%s", event_type)
        raise HTTPException(502, str(exc)) from exc

    return {"received": True}

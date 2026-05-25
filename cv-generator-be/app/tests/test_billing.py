import asyncio
from collections.abc import Generator
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import billing
from app.db import Base
from app.models import Subscription, User
from app.services.subscriptions import has_paid_access
from app.src.connections.stripe_connection.stripe_connection import StripeConfigurationError


@pytest.fixture
def db_user() -> Generator[tuple[Session, User], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as db:
        user = User(idp_sub="clerk-user", email="user@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        yield db, user


def _stripe_subscription(
    user: User,
    *,
    status: str = "active",
    subscription_id: str = "sub_123",
    customer_id: str = "cus_123",
    price_id: str = "price_123",
) -> dict[str, Any]:
    return {
        "id": subscription_id,
        "customer": customer_id,
        "status": status,
        "metadata": {
            "user_id": str(user.id),
            "subscription_type": "pro",
        },
        "items": {
            "data": [
                {
                    "price": {"id": price_id},
                    "current_period_end": 1_893_456_000,
                }
            ]
        },
    }


def test_checkout_session_creates_customer_and_embedded_session(
    db_user: tuple[Session, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, user = db_user
    created_customer: dict[str, str | None] = {}
    created_checkout: dict[str, Any] = {}

    def fake_create_customer(*, email: str, name: str | None = None) -> dict[str, str]:
        created_customer.update({"email": email, "name": name})
        return {"id": "cus_123"}

    def fake_create_checkout_session(**kwargs: Any) -> dict[str, str]:
        created_checkout.update(kwargs)
        return {"id": "cs_123", "client_secret": "cs_secret_123"}

    monkeypatch.setattr(billing, "create_customer", fake_create_customer)
    monkeypatch.setattr(billing, "create_checkout_session", fake_create_checkout_session)

    response = billing.checkout_session(current_user=user, db=db)

    assert response.client_secret == "cs_secret_123"
    assert response.session_id == "cs_123"
    assert created_customer == {"email": "user@example.com", "name": "user@example.com"}
    assert created_checkout == {"stripe_customer_id": "cus_123", "user_id": user.id}
    assert user.stripe_customer_id == "cus_123"


def test_checkout_session_rejects_existing_active_subscription(
    db_user: tuple[Session, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, user = db_user
    db.add(
        Subscription(
            user_id=user.id,
            subscription_type="pro",
            active=True,
            status="active",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
        )
    )
    db.commit()

    monkeypatch.setattr(
        billing,
        "create_checkout_session",
        lambda **_: pytest.fail("Stripe should not be called"),
    )

    with pytest.raises(HTTPException) as exc:
        billing.checkout_session(current_user=user, db=db)

    assert exc.value.status_code == 409


def test_checkout_session_reports_missing_stripe_configuration(
    db_user: tuple[Session, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, user = db_user
    user.stripe_customer_id = "cus_123"
    db.commit()

    def fail_checkout(**_: Any) -> None:
        raise StripeConfigurationError("STRIPE_PRO_PRICE_ID is not configured")

    monkeypatch.setattr(billing, "create_checkout_session", fail_checkout)

    with pytest.raises(HTTPException) as exc:
        billing.checkout_session(current_user=user, db=db)

    assert exc.value.status_code == 500
    assert exc.value.detail == "STRIPE_PRO_PRICE_ID is not configured"


def test_sync_subscription_from_stripe_upserts_active_subscription(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user

    row = billing._sync_subscription_from_stripe(  # noqa: SLF001
        db,
        _stripe_subscription(user),
    )

    assert row is not None
    assert row.user_id == user.id
    assert row.subscription_type == "pro"
    assert row.active is True
    assert row.status == "active"
    assert row.stripe_customer_id == "cus_123"
    assert row.stripe_subscription_id == "sub_123"
    assert row.stripe_price_id == "price_123"
    assert row.current_period_end is not None
    assert has_paid_access(db, user) is True


def test_sync_subscription_from_stripe_updates_inactive_status(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user
    billing._sync_subscription_from_stripe(db, _stripe_subscription(user))  # noqa: SLF001

    row = billing._sync_subscription_from_stripe(  # noqa: SLF001
        db,
        _stripe_subscription(user, status="canceled"),
    )

    assert row is not None
    assert row.active is False
    assert row.status == "canceled"
    assert has_paid_access(db, user) is False
    assert len(db.scalars(select(Subscription)).all()) == 1


def test_get_subscription_returns_latest_subscription(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user
    db.add(
        Subscription(
            user_id=user.id,
            subscription_type="pro",
            active=False,
            status="canceled",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_old",
        )
    )
    db.add(
        Subscription(
            user_id=user.id,
            subscription_type="pro",
            active=True,
            status="active",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_new",
        )
    )
    db.commit()

    response = billing.get_subscription(current_user=user, db=db)

    assert response.subscription_type == "pro"
    assert response.active is True
    assert response.status == "active"


def test_webhook_verifies_signature_and_syncs_subscription(
    db_user: tuple[Session, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, user = db_user

    class RequestStub:
        async def body(self) -> bytes:
            return b'{"id":"evt_123"}'

    def fake_construct_webhook_event(payload: bytes, signature: str | None) -> dict[str, Any]:
        assert payload == b'{"id":"evt_123"}'
        assert signature == "sig_123"
        return {
            "type": "customer.subscription.updated",
            "data": {"object": _stripe_subscription(user)},
        }

    monkeypatch.setattr(billing, "construct_webhook_event", fake_construct_webhook_event)

    response = asyncio.run(
        billing.stripe_webhook(
            request=RequestStub(),  # type: ignore[arg-type]
            db=db,
            stripe_signature="sig_123",
        )
    )

    assert response == {"received": True}
    subscription = db.scalar(select(Subscription))
    assert subscription is not None
    assert subscription.active is True

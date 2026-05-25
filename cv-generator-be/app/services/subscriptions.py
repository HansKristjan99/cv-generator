from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subscription, User


def has_paid_access(db: Session, user: User) -> bool:
    if user.is_unlimited:
        return True
    return bool(
        db.scalar(
            select(Subscription.id).where(
                Subscription.user_id == user.id,
                Subscription.active.is_(True),
            )
        )
    )

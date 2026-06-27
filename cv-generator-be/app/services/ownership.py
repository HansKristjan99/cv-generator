"""Fetch a user-owned row by id, or 404.

Every CRUD route needs the same check: "load row X with this id, but only if it
belongs to the current user, otherwise 404." This is the single source of truth
for that pattern so it isn't re-implemented (subtly differently) in each router.
"""

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_owned_or_none(
    db: Session, model: Any, item_id: UUID | None, user_id: UUID
) -> Any | None:
    """Return the row owned by ``user_id`` with this id, or ``None``."""
    if item_id is None:
        return None
    return db.scalar(
        select(model).where(model.id == item_id, model.user_id == user_id)
    )


def get_owned(
    db: Session,
    model: Any,
    item_id: UUID | None,
    user_id: UUID,
    *,
    not_found: str = "Not found.",
) -> Any:
    """Return the user-owned row, or raise ``404`` with ``not_found``."""
    item = get_owned_or_none(db, model, item_id, user_id)
    if item is None:
        raise HTTPException(404, not_found)
    return item

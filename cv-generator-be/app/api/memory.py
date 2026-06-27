"""`/users/memory` — read and patch the user's stored CV profile.

DTOs live in ``schemas/user_memory.py`` and the load/upsert logic in
``services/memory_crud.py``; this module is just the HTTP surface.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.user_memory import UserMemoryOut, UserMemoryPatch
from app.services.auth import CurrentUser
from app.services.memory_crud import apply_memory_patch, load_memory

router = APIRouter(prefix="/users/memory", tags=["users"])


@router.get("", response_model=UserMemoryOut)
def get_user_memory(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserMemoryOut:
    return load_memory(db, current_user.id)


@router.post("", response_model=UserMemoryOut)
def update_user_memory(
    payload: UserMemoryPatch,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserMemoryOut:
    apply_memory_patch(db, current_user.id, payload)
    return load_memory(db, current_user.id)

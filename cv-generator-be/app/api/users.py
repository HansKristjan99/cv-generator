from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Template
from app.services.auth import CurrentUser

router = APIRouter(prefix="/users", tags=["users"])


class UserOut(BaseModel):
    id: UUID
    idp_sub: str
    email: str

    model_config = {"from_attributes": True}


class UserSettings(BaseModel):
    preferred_template_id: UUID | None


class UserSettingsPatch(BaseModel):
    preferred_template_id: UUID | None


@router.get("/me", response_model=UserOut)
def get_current_user(user: CurrentUser):
    return user


@router.post("/me", response_model=UserOut)
def register_current_user(user: CurrentUser):
    return user


@router.get("/settings", response_model=UserSettings)
def get_user_settings(user: CurrentUser):
    return UserSettings(preferred_template_id=user.preferred_template_id)


@router.patch("/settings", response_model=UserSettings)
def update_user_settings(
    payload: UserSettingsPatch,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserSettings:
    if payload.preferred_template_id is not None:
        template = db.query(Template).filter(Template.id == payload.preferred_template_id).first()
        if not template:
            raise HTTPException(404, "Template not found.")
    user.preferred_template_id = payload.preferred_template_id
    db.commit()
    db.refresh(user)
    return UserSettings(preferred_template_id=user.preferred_template_id)

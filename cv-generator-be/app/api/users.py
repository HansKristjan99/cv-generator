from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.auth import CurrentUser

router = APIRouter(prefix="/users", tags=["users"])


class UserOut(BaseModel):
    id: UUID
    idp_sub: str
    email: str

    model_config = {"from_attributes": True}


@router.get("/me", response_model=UserOut)
def get_current_user(user: CurrentUser):
    return user


@router.post("/me", response_model=UserOut)
def register_current_user(user: CurrentUser):
    return user

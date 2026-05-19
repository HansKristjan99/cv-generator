"""Template catalogue — GET /templates/."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Template

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[TemplateOut])
def list_templates(db: Annotated[Session, Depends(get_db)]) -> list[Template]:
    return db.query(Template).order_by(Template.name).all()

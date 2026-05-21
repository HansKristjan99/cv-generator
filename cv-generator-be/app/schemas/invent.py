"""Schemas for fabricated answers to clarifying questions."""

from pydantic import BaseModel, Field


class InventedAnswer(BaseModel):
    """A fabricated but realistic answer to one clarifying question."""

    question: str = Field(..., description="The clarifying question, copied verbatim.")
    invented_answer: str = Field(
        ...,
        description=(
            "A realistic, specific, fabricated professional experience answering the question — "
            "concrete technologies, scope and plausible metrics, consistent with the candidate's "
            "stated seniority, employers, timeline and background. Written as a first-person "
            "statement, as if the candidate were answering."
        ),
    )


class InventedExperience(BaseModel):
    """Fabricated answers covering every clarifying question."""

    answers: list[InventedAnswer] = Field(..., description="One entry per clarifying question.")

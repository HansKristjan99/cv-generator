

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """One requirement extracted from the job description, paired with evidence from the CV."""

    requirement: str = Field(
        ...,
        description="A single requirement lifted verbatim or tightly paraphrased from the job description.",
    )
    why_satisfied_by_cv: str = Field(
        ...,
        description=(
            "Point to the exact part of the CV that satisfies this requirement "
            "(role, project, skill, education, etc.). "
            "If nothing in the CV satisfies it, write the literal string 'Not satisfied'."
        ),
    )

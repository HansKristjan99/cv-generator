from typing import Union
from pydantic import BaseModel, Field

from app.src.schemas.output_types.responses.cv.cv import CurriculumVitae
from app.src.schemas.output_types.responses.cv.cv_questions import QuestionsToImproveCv


class CVWriterResponse(BaseModel):
    """Top-level model output: the generated CV plus a per-requirement audit against the job description."""


    content: Union[CurriculumVitae, QuestionsToImproveCv] = Field(
        ...,
        description=(
            "The generated CV. If the CV does not satisfy all requirements well, this field contains a list of questions to improve the CV instead, and `curriculum_vitae` will be empty."
        ),
    )

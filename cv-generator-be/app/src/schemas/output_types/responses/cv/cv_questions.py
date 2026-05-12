
from pydantic import BaseModel, Field


class QuestionsToImproveCv(BaseModel):
    """Questions to help improve the CV based on the job description."""
    type : str = Field(default="questions")
    questions: list[QuestionToImproveCv] = Field(
        ...,
        description="A list of questions aimed at uncovering more information to strengthen the CV. Only include if the CV is not covering all requirements comfortably" + 
        "If the CV already satisfies all requirements well, don't return this object."
    )

class QuestionToImproveCv(BaseModel):
    """A single question to help improve the CV based on the job description."""
    question: str = Field(
        ...,
        description="A question aimed at uncovering more information to strengthen the CV. Only include if the CV is not covering all requirements comfortably" + 
        "If the CV already satisfies all requirements well, don't return this object." + 
        "Example: 'Can you tell me more about your experience with React? The job description emphasizes React experience, but your CV doesn't mention it.'"
        "Example 2: How did you do testing and QA at Microsoft? Elaborate on frameworks or technologies you used you use?"
    )

    corresponding_requirement: str = Field(
        ...,
        description="The specific requirement from the job description that this question is targeting, but the candidate didn't satisfy yet."
    )
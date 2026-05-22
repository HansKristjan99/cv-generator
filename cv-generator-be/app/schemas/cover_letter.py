"""Cover-letter schemas: structured letter for LaTeX rendering, plus plain replies.

Fields are declared required (`Field(...)`) even when nullable, because OpenAI
structured outputs require every property in `required`; optionality is expressed
through the nullable type, not a default. Free-text fields are written as plain
prose — the server escapes LaTeX special characters before rendering.
"""

from typing import Union

from pydantic import BaseModel, Field

from app.schemas.cv import OtherMessage


class CoverLetter(BaseModel):
    """A one-page cover letter tailored to a job description.

    The body carries the letter's prose (3-4 short paragraphs); the greeting,
    recipient, closer, and sender contact details live in their own fields so the
    template can lay out a proper business letter.
    """

    name: str = Field(..., description="Candidate full name, for the header and signature.")
    title: str = Field(
        ...,
        description=(
            "Candidate's professional title shown under the signature "
            "(e.g. 'Software Engineer'). Empty string if none is supported by the inputs."
        ),
    )
    email: str = Field(..., description="Candidate contact email.")
    phone: str | None = Field(..., description="Candidate phone in international format, or null.")
    location: str = Field(..., description="Candidate city + country.")
    linkedin: str | None = Field(
        ..., description="Full LinkedIn profile URL, or null if not provided."
    )
    recipient: str = Field(
        ...,
        description=(
            "Who the letter is addressed to. Use the recruiter or hiring-manager name "
            "if the inputs provide one; otherwise the literal string 'Hiring Team'."
        ),
    )
    company: str = Field(
        ...,
        description="Company the candidate is applying to, or empty string if unknown.",
    )
    greeting: str = Field(
        ..., description="Salutation word, normally 'Dear'. Combined as '<greeting> <recipient>,'."
    )
    body: str = Field(
        ...,
        description=(
            "The letter body as plain text: 3-4 short paragraphs separated by a single "
            "blank line. Do NOT include the greeting line or the sign-off/name here — "
            "those are separate fields. 300-380 words, plain prose, no markdown."
        ),
    )
    closer: str = Field(..., description="Sign-off word before the signature, normally 'Sincerely'.")


class CoverLetterWriterResponse(BaseModel):
    """Top-level CoverLetterAgent output: a letter, or a plain-text reply."""

    content: Union[CoverLetter, OtherMessage] = Field(
        ...,
        description=(
            "Pick exactly one variant: "
            "(1) CoverLetter — the user wants a cover letter generated or updated; "
            "(2) OtherMessage — plain-text reply for conversational turns, refusals, or "
            "messages that don't require producing a letter."
        ),
    )

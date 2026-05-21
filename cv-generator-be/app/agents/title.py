"""SessionTitleAgent — names a CV-tailoring session for the chat sidebar."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You write concise titles (3-6 words) for CV-tailoring sessions. "
    "Name the role and company if both are visible (e.g. 'Backend Engineer at Vercel'). "
    "If the company is missing, name the role and a distinguishing detail. "
    "No quotes, no trailing punctuation."
)


class _SessionTitle(BaseModel):
    title: str


class SessionTitleAgent:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    def run(self, job_description: str | None, user_message: str) -> str | None:
        if not job_description:
            return None
        prompt = (
            f"Job description:\n{job_description[:1200]}\n\n"
            f"User's first message:\n{user_message[:300] or '(none)'}"
        )
        try:
            result, _ = self.client.get_structured_output(
                prompt, _SessionTitle, system_prompt=SYSTEM_PROMPT,
            )
        except Exception:
            logger.exception("SessionTitleAgent failed")
            return None
        if not result or not result.title:
            return None
        return result.title.strip().strip('"').strip("'")[:80]

"""MemoryAgent — diffs new CV/profile facts against what's already stored for the user."""

from __future__ import annotations

import logging
from pathlib import Path

from app.schemas import MemoryExtraction, NewUserData
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You diff new CV/profile facts against what is already stored for the user.
CURRENT STORED USER DATA is the ground truth of what is already known.
Extract only facts explicitly present in the latest input or attached file.
Do not infer, normalize aggressively, or invent missing values.
A job is already stored if CURRENT STORED USER DATA contains an entry with the same company and title.
An education entry is already stored if CURRENT STORED USER DATA contains the same institution and degree.
A project is already stored if CURRENT STORED USER DATA contains the same project title.
A skill is already stored if CURRENT STORED USER DATA lists it under any category.
An award is already stored if CURRENT STORED USER DATA contains the same award title.
Only return items that have NO match in CURRENT STORED USER DATA.
Prefer structured categories over freeform notes. Use notes only for concise, durable,
CV-relevant facts that do not fit jobs, education, skill categories, projects, or awards.
Group skills under clear categories like Frontend, Backend, Infrastructure,
Languages, Security, or similarly compact user-specific names. Do not over-categorize.
Return {"new_user_data": null} when there is nothing new.
""".strip()


class MemoryAgent:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    def extract(
        self,
        *,
        stored_user_data: str,
        user_message: str,
        assistant_response: str,
        source_text: str | None,
        job_description: str | None,
        file: Path | None,
    ) -> NewUserData | None:
        prompt = (
            f"CURRENT STORED USER DATA:\n{stored_user_data}\n\n"
            f"LATEST USER MESSAGE:\n{user_message}\n\n"
            f"LATEST ASSISTANT RESPONSE:\n{assistant_response}\n\n"
            f"SOURCE CV TEXT, IF PROVIDED:\n{source_text or '(none)'}\n\n"
            f"JOB DESCRIPTION, IF PROVIDED:\n{job_description or '(none)'}"
        )
        parsed, _ = self.client.get_structured_output(
            prompt, MemoryExtraction,
            file=file, system_prompt=SYSTEM_PROMPT, max_tool_iterations=1,
        )
        return parsed.new_user_data if parsed else None

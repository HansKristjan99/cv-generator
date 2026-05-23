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

DEDUPLICATION — match on MEANING, not exact characters. A fact is already stored
(do NOT return it) if the same information is already present in ANY wording,
order, tense, or phrasing — even if the metrics, words, or level of detail differ.
Returning a reworded version of something already stored is a mistake. Specifically:
- A job is already stored if the same company and title appear.
- A job bullet/achievement is already stored if the same accomplishment appears
  under that job in any wording — do not add paraphrases or metric re-statements.
- An education entry is already stored if the same institution and degree appear.
- A project is already stored if the same title appears.
- A skill is already stored if the same keyword appears (case-insensitive).
- An award is already stored if the same title appears.
- A note is already stored if its meaning is already captured anywhere above.
Only return genuinely new items.

Skills are a FLAT list of individual keyword strings — no categories, no
proficiency (e.g. "React", "PostgreSQL", "Kubernetes"). Return only new keywords.
Use notes only for concise, durable, CV-relevant facts that do not fit jobs,
education, skills, projects, or awards.
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

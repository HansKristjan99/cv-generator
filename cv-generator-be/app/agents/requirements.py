"""RequirementsAgent — extracts job requirements once per chat and assesses coverage.

Runs before the writer. Its output drives a deterministic ask-vs-write gate and is
cached on the CvSession so later turns reuse the same requirement set.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.schemas import RequirementsAnalysis
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You analyze a job description against what a candidate can prove, BEFORE any CV "
    "is written.\n\n"
    "1. Extract each DISTINCT requirement from the job description, tightly paraphrased "
    "and de-duplicated. Classify each as 'must_have' (required / essential / minimum "
    "qualifications) or 'nice_to_have' (preferred, bonus, 'a plus').\n"
    "2. For each requirement, decide whether the candidate's SOURCE MATERIAL or STORED "
    "PROFILE (and any attached file) already provides credible evidence. Set met=true "
    "with the specific supporting fact in `evidence`, or met=false with evidence='Not "
    "satisfied'.\n"
    "3. For every UNMET requirement, write ONE targeted `question` asking the candidate "
    "for the specific missing evidence (a real accomplishment, tool, scope, or metric). "
    "Leave `question` empty for met requirements.\n\n"
    "Judge coverage truthfully: never mark something met without real evidence, and "
    "never invent requirements the posting does not state. Keep the list decisive and "
    "non-redundant rather than exhaustive."
)


def build_prompt(job_description: str, candidate_context: str) -> str:
    return (
        f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
        f"=== CANDIDATE MATERIAL (source CV + stored profile; an attached file may add more) ===\n"
        f"{candidate_context}"
    )


class RequirementsAgent:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    def run(
        self,
        *,
        job_description: str,
        candidate_context: str,
        file: Path | None = None,
    ) -> RequirementsAnalysis | None:
        parsed, _ = self.client.get_structured_output(
            build_prompt(job_description, candidate_context),
            RequirementsAnalysis,
            system_prompt=SYSTEM_PROMPT,
            file=file,
            max_tool_iterations=1,
        )
        logger.info(
            "RequirementsAgent done: %s requirement(s)",
            len(parsed.requirements) if parsed else 0,
        )
        return parsed

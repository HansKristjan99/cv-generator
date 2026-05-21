"""InventAgent — drafts plausible answers to clarifying questions on behalf of the candidate."""

from __future__ import annotations

import logging

from app.schemas import InventedExperience, QuestionToImproveCv
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a CV assistant that drafts answers to clarifying interview-style questions "
    "on behalf of a job candidate. The candidate does not want to write the answers "
    "themselves, so you invent realistic professional experience that answers each "
    "question. The candidate will review and edit your draft before using it.\n\n"
    "Produce exactly one answer per clarifying question.\n\n"
    "Each invented answer must:\n"
    "- Be SPECIFIC and CONCRETE: name plausible technologies, tools, team sizes, and "
    "system/project scope. Never use vague filler like 'worked on', 'exposure to', "
    "or 'familiar with'.\n"
    "- Include BELIEVABLE, MODEST metrics (latency, throughput, incident counts, "
    "adoption, %, time saved) that are realistic for the candidate's seniority and "
    "employer size. Never inflate or exaggerate.\n"
    "- Be FULLY CONSISTENT with the candidate's stored profile and the conversation so "
    "far: attribute invented work to a role, employer, and time window the candidate "
    "already has on record. Never invent a new employer and never contradict stated "
    "dates, titles, or facts.\n"
    "- Directly satisfy the job requirement the question targets, without keyword-stuffing.\n"
    "- Be INTERVIEW-DEFENSIBLE: plausible enough that the candidate could answer "
    "follow-up questions about it.\n"
    "- Be written in the FIRST PERSON, in the candidate's voice, as a natural answer "
    "to the question.\n\n"
    "Do not write a CV. Only return the per-question answers."
)


def build_prompt(
    user_memory: str,
    transcript: str,
    job_description: str,
    questions: list[QuestionToImproveCv],
) -> str:
    questions_block = "\n\n".join(
        f"QUESTION: {q.question}\nTARGET REQUIREMENT: {q.corresponding_requirement}"
        for q in questions
    )
    return (
        f"=== CANDIDATE'S STORED PROFILE ===\n{user_memory or '(none)'}\n\n"
        f"=== CONVERSATION SO FAR ===\n{transcript or '(none)'}\n\n"
        f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
        f"=== CLARIFYING QUESTIONS TO ANSWER ===\n{questions_block}\n\n"
        "Invent one realistic, plausible answer for each clarifying question above, "
        "so that its target requirement becomes satisfied."
    )


class InventAgent:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    def run(
        self,
        *,
        user_memory: str,
        transcript: str,
        job_description: str,
        questions: list[QuestionToImproveCv],
    ) -> InventedExperience | None:
        prompt = build_prompt(user_memory, transcript, job_description, questions)
        invented, _ = self.client.get_structured_output(
            prompt, InventedExperience, system_prompt=SYSTEM_PROMPT,
        )
        return invented

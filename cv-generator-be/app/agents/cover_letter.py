"""CoverLetterAgent — drafts a tailored cover letter and self-corrects via a compile tool.

Mirrors WriterAgent: a single LLM call drafts a CoverLetter, then uses the
`compile_cover_letter` tool to render it to PDF and read back the page count,
iterating until it fits one page. Free-text fields are escaped for LaTeX on the
server, so the model writes plain text only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas import CoverLetter, CoverLetterWriterResponse
from app.services.latex import compile_latex_to_pdf, cover_letter_to_latex
from app.services.latex_escape import escape_cover_letter_for_latex
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 6
_TARGET_PAGES = 1


SYSTEM_PROMPT = (
    "You are an expert tech cover-letter writer.\n\n"

    "TASK\n"
    "Write one cover letter tailored to the job description (JD) using only the facts "
    "provided in the candidate's CV, stored profile, the JD, and any optional notes in "
    "the user's message. The CV, JD, and notes are supplied in the user turn.\n\n"

    "NON-NEGOTIABLE RULES\n"
    "- Use evidence only. Do not invent, embellish, or infer unsupported facts.\n"
    "- If a recruiter or hiring-manager name is not provided, address the letter to the "
    "'Hiring Team'.\n"
    "- Plain text only in the body. No markdown, no bullet points, no headings.\n"
    "- Default length: 300-380 words.\n"
    "- Default structure: 4 short paragraphs.\n"
    "- If any detail is unspecified, treat it as unspecified and do not guess.\n\n"

    "INTERNAL METHOD\n"
    "1. Identify the top 3-5 requirements, responsibilities, or signals in the JD.\n"
    "2. Map each one to the strongest supporting evidence in the CV/profile.\n"
    "3. Choose the 2-3 best proof points for the letter.\n"
    "4. Omit any claim that cannot be directly supported by the CV, JD, or notes.\n"
    "5. Before finalizing, verify every name, title, company, date, metric, tool, and "
    "achievement against the inputs.\n\n"

    "WRITING GOALS\n"
    "- Sound like a strong human applicant, not a generic assistant.\n"
    "- Be professional, specific, concise, and warm.\n"
    "- Front-load role fit in the opening paragraph.\n"
    "- Use 2-3 evidence-based achievements with metrics, scale, scope, reliability, "
    "shipping, business impact, user impact, or process improvement when available.\n"
    "- Add one credible personalization hook from the JD or optional notes. If none "
    "exists, personalize to the role or problem space rather than inventing company facts.\n"
    "- Be ATS-aware but human-first: naturally reuse important JD terminology for skills, "
    "tools, and domains only when it is true of the candidate.\n"
    "- Adapt emphasis to the role: for startup or builder roles, emphasize ownership, "
    "pace, ambiguity, and shipping; for platform or enterprise roles, emphasize scale, "
    "reliability, security, stakeholder management, and systems thinking; if seniority or "
    "company size is unspecified, do not infer them.\n\n"

    "STYLE RULES\n"
    "- Keep sentences concrete and readable.\n"
    "- Do not restate the CV line by line.\n"
    "- Do not overuse 'I'.\n"
    "- Do not use cliches, stacked adjectives, empty self-labels, or corporate-speak.\n"
    "- Avoid phrases like: 'I am writing to express my interest', 'My name is', 'dynamic "
    "and detail-oriented', 'results-driven team player', 'proven ability to leverage "
    "cross-functional collaboration', 'think outside the box', 'move the needle', 'value "
    "add', 'perfect candidate'.\n"
    "- Do not copy the JD sentence-for-sentence.\n"
    "- Do not include fake familiarity with the company or unsupported enthusiasm.\n\n"

    "LETTER SHAPE (the body field)\n"
    "Paragraph 1: specific hook tied to the role or company + strongest fit summary.\n"
    "Paragraph 2: strongest achievement, with evidence and outcome.\n"
    "Paragraph 3: second achievement + collaboration, communication, or working style "
    "relevant to the JD.\n"
    "Paragraph 4: credible motivation for this role or company + concise close.\n\n"

    "OUTPUT FORMAT — return a structured CoverLetter (NOT free text):\n"
    "- name, title, email, phone, location, linkedin: the candidate's details, taken "
    "from the CV/profile (use empty string / null when a detail is unsupported).\n"
    "- recipient: the hiring manager or recruiter name if the inputs give one, otherwise "
    "the literal 'Hiring Team'.\n"
    "- company: the company name from the JD, or empty string if unknown.\n"
    "- greeting: 'Dear'. closer: 'Sincerely'.\n"
    "- body: the 4 short paragraphs as plain text, separated by a single blank line. Do "
    "NOT put the greeting line or the sign-off/name inside body — those are separate "
    "fields.\n"
    "Use the OtherMessage variant instead for conversational turns, refusals, or any "
    "message that does not call for a letter.\n\n"

    "TEXT FORMATTING:\n"
    "Write every field as plain prose — no LaTeX, markdown, or HTML, and no character "
    "escaping. The server escapes special characters (& % $ # _ { } ~ ^ \\) for you, so "
    "write '50%' not '50\\%'.\n\n"

    "COMPILE-AND-CHECK LOOP — REQUIRED before returning any CoverLetter:\n"
    "The `compile_cover_letter` tool renders the letter to PDF and returns `page_count` "
    "and `fits_target`, attaching the PDF so you can SEE the result.\n"
    " 1. Draft the letter.\n"
    " 2. Call `compile_cover_letter` with the full draft.\n"
    " 3. If it spills onto a second page, tighten the prose and trim the weakest "
    "sentences until it fits on one page; keep it within 300-380 words.\n"
    " 4. Re-compile after each revision. Return the letter only once `fits_target` is "
    "true. Do NOT call the tool for an OtherMessage reply.\n\n"

    "FINAL CHECK — silently confirm: every substantive claim is supported; metrics have "
    "enough context to sound credible; no invented company facts appear; the wording "
    "sounds human and role-specific; the letter could not be sent unchanged to 100 "
    "companies."
)


def _compile_tool_schema() -> dict[str, Any]:
    """A `compile_cover_letter` function tool whose parameters are the CoverLetter schema."""
    return {
        "type": "function",
        "name": "compile_cover_letter",
        "description": (
            "Render a cover letter to PDF and return its page count so you can check it "
            "fits on one page before finalizing. Pass the full letter as plain text (the "
            "server escapes LaTeX characters for you). The rendered PDF is attached to "
            "the next turn so you can review the layout."
        ),
        "parameters": CoverLetter.model_json_schema(),
    }


def _compile_handler():
    def _handle(name: str, args: dict[str, Any]):
        try:
            cl = CoverLetter.model_validate(args)
        except Exception as exc:
            logger.warning("compile_cover_letter received invalid args: %s", exc)
            return {"success": False, "error": f"Invalid cover-letter payload: {exc}"}
        latex = cover_letter_to_latex(escape_cover_letter_for_latex(cl))
        result = compile_latex_to_pdf(latex)
        payload: dict[str, Any] = {
            "success": result.success,
            "page_count": result.page_count,
            "required_pages": _TARGET_PAGES,
            "fits_target": result.success and result.page_count == _TARGET_PAGES,
        }
        if not result.success:
            payload["error"] = (result.error or "(no error)")[-600:]
        logger.info(
            "compile_cover_letter: success=%s page_count=%d",
            result.success, result.page_count,
        )
        return payload, (result.pdf_bytes if result.success else None)
    return _handle


@dataclass
class CoverLetterResult:
    response: CoverLetterWriterResponse
    conversation_id: str


class CoverLetterAgent:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    def run(
        self,
        prompt_input: str,
        *,
        file: Path | None = None,
        conversation_id: str | None = None,
    ) -> CoverLetterResult:
        parsed, conv_id = self.client.get_structured_output(
            prompt_input,
            CoverLetterWriterResponse,
            system_prompt=SYSTEM_PROMPT,
            file=file,
            conversation_id=conversation_id,
            tools=[_compile_tool_schema()],
            tool_handler=_compile_handler(),
            max_tool_iterations=_MAX_TOOL_ITERATIONS,
        )
        if parsed is None:
            raise RuntimeError("CoverLetterAgent: model returned no parsed output.")
        logger.info("CoverLetterAgent done variant=%s", type(parsed.content).__name__)
        return CoverLetterResult(response=parsed, conversation_id=conv_id)

"""LLM-backed agents. Each module is one agent with its own prompt and tools."""

from app.agents.cover_letter import CoverLetterAgent
from app.agents.invent import InventAgent
from app.agents.memory import MemoryAgent
from app.agents.requirements import RequirementsAgent
from app.agents.title import SessionTitleAgent
from app.agents.writer import WriterAgent

__all__ = [
    "CoverLetterAgent",
    "InventAgent",
    "MemoryAgent",
    "RequirementsAgent",
    "SessionTitleAgent",
    "WriterAgent",
]

import json
from pathlib import Path
from typing import Any, Callable, Tuple, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import OPENAI_CONVERSATION_ITEM_CHAR_CAP, OPENAI_DEFAULT_TOOL_ITERATIONS
from app.src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

ToolHandler = Callable[[str, dict[str, Any]], dict[str, Any]]


class OpenAIClient:
    def __init__(self, model_str: str) -> None:
        self.client = OpenAI()
        self.model_str = model_str

    def get_response(self, text: str) -> str:
        response = self.client.responses.create(
            model=self.model_str,
            input=text,
        )
        return response.output_text

    def get_conversation_transcript(
        self,
        conversation_id: str,
        item_char_cap: int = OPENAI_CONVERSATION_ITEM_CHAR_CAP,
    ) -> str:
        """Render a conversation's user/assistant turns as plain text. Read-only.

        Skips the system prompt and soft-caps each item so a long conversation
        (e.g. one carrying compiled CV LaTeX) does not produce an oversized prompt.
        Lets the OpenAI client raise (e.g. NotFoundError) for an unknown id.
        """
        items = self.client.conversations.items.list(conversation_id, order="asc")
        lines: list[str] = []
        for item in items:
            role = getattr(item, "role", None)
            if role not in ("user", "assistant"):
                continue
            parts = getattr(item, "content", None) or []
            texts = [text for part in parts if (text := getattr(part, "text", None))]
            if not texts:
                continue
            body = "\n".join(texts).strip()
            if len(body) > item_char_cap:
                body = body[:item_char_cap] + " […truncated]"
            lines.append(f"{role.upper()}: {body}")
        return "\n\n".join(lines)

    def init_conversation(self, system_prompt: str) -> str:
        conversation = self.client.conversations.create(
            items=[
                {"role": "system", "content": system_prompt}
            ]
        )
        return conversation.id

    def get_structured_output(
        self,
        text: str,
        output_structure: type[T],
        file: Path | None = None,
        system_prompt: str | None = None,
        conversation_id: str | None = None,
        tools: list[dict] | None = None,
        tool_handler: ToolHandler | None = None,
        max_tool_iterations: int = OPENAI_DEFAULT_TOOL_ITERATIONS,
    ) -> Tuple[T | None, str]:
        if not conversation_id:
            conversation_id = self.init_conversation(system_prompt or "")

        content: list[dict] = [{"type": "input_text", "text": text}]
        if file is not None:
            with open(file, "rb") as f:
                uploaded = self.client.files.create(file=f, purpose="user_data")
            logger.debug("Uploaded file to OpenAI: file_id=%s", uploaded.id)
            content.append({"type": "input_file", "file_id": uploaded.id})

        next_input: list[dict] = [{"role": "user", "content": content}]
        response = None

        for iteration in range(max_tool_iterations):
            logger.debug(
                "OpenAI responses.parse model=%s conversation=%s iteration=%d/%d",
                self.model_str, conversation_id, iteration + 1, max_tool_iterations,
            )
            response = self.client.responses.parse(
                model=self.model_str,
                input=next_input,
                text_format=output_structure,
                conversation=conversation_id,
                tools=tools or [],
            )
            function_calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]
            if not function_calls:
                return response.output_parsed, conversation_id
            logger.info("OpenAI requested %d tool call(s)", len(function_calls))
            if tool_handler is None:
                raise RuntimeError("Model invoked a tool but no handler was provided")
            next_input = [
                {
                    "type": "function_call_output",
                    "call_id": fc.call_id,
                    "output": json.dumps(tool_handler(fc.name, json.loads(fc.arguments))),
                }
                for fc in function_calls
            ]

        logger.warning("Exhausted %d tool iterations without a final response", max_tool_iterations)
        return (response.output_parsed if response else None), conversation_id

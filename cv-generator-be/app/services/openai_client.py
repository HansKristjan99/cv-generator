import json
import logging
from pathlib import Path
from typing import Any, Callable, Tuple, TypeVar

from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Tool handlers may return a plain result dict or a (result, pdf_bytes) tuple.
# When pdf_bytes is present, get_structured_output uploads the PDF to OpenAI
# and attaches it to the next input turn so the model can review the render.
ToolHandlerResult = dict[str, Any] | tuple[dict[str, Any], bytes | None]
ToolHandler = Callable[[str, dict[str, Any]], ToolHandlerResult]

# Soft cap per conversation item so a long transcript (e.g. one carrying compiled
# CV LaTeX) does not produce an oversized prompt.
_ITEM_CHAR_CAP = 4000

# Number of responses.parse rounds. Allows up to 3 tool (compile) calls plus a
# final round that returns the parsed answer — see CV_SYSTEM_PROMPT.
_MAX_TOOL_ITERATIONS = 4


class OpenAIClient:
    def __init__(self, model_str: str) -> None:
        self.client = OpenAI()
        self.model_str = model_str

    def get_response(self, text: str) -> str:
        response = self.client.responses.create(model=self.model_str, input=text)
        return response.output_text

    def get_conversation_transcript(self, conversation_id: str) -> str:
        """Render a conversation's user/assistant turns as plain text. Read-only.

        Skips the system prompt and soft-caps each item. Lets the OpenAI client
        raise (e.g. NotFoundError) for an unknown id.
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
            if len(body) > _ITEM_CHAR_CAP:
                body = body[:_ITEM_CHAR_CAP] + " […truncated]"
            lines.append(f"{role.upper()}: {body}")
        return "\n\n".join(lines)

    def init_conversation(self, system_prompt: str) -> str:
        conversation = self.client.conversations.create(
            items=[{"role": "system", "content": system_prompt}]
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
        max_tool_iterations: int = _MAX_TOOL_ITERATIONS,
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
            next_input = []
            for fc in function_calls:
                raw = tool_handler(fc.name, json.loads(fc.arguments))
                if isinstance(raw, tuple):
                    result_dict, pdf_bytes = raw
                else:
                    result_dict, pdf_bytes = raw, None
                next_input.append({
                    "type": "function_call_output",
                    "call_id": fc.call_id,
                    "output": json.dumps(result_dict),
                })
                if pdf_bytes:
                    try:
                        uploaded = self.client.files.create(
                            file=("cv.pdf", pdf_bytes, "application/pdf"),
                            purpose="user_data",
                        )
                        next_input.append({
                            "role": "user",
                            "content": [{"type": "input_file", "file_id": uploaded.id}],
                        })
                        logger.debug("Uploaded compiled PDF to OpenAI: file_id=%s", uploaded.id)
                    except Exception:
                        logger.warning("Failed to upload compiled PDF to OpenAI; continuing without it")

        logger.warning("Exhausted %d tool iterations without a final response", max_tool_iterations)
        return (response.output_parsed if response else None), conversation_id

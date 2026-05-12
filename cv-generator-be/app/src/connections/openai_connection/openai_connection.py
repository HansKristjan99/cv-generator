import json
from pathlib import Path
from typing import Any, Callable, Tuple, TypeVar

from openai import OpenAI
from pydantic import BaseModel

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
        max_tool_iterations: int = 4,
    ) -> Tuple[T | None, str]:
        if not conversation_id:
            conversation_id = self.init_conversation(system_prompt or "")

        content: list[dict] = [{"type": "input_text", "text": text}]
        if file is not None:
            with open(file, "rb") as f:
                uploaded = self.client.files.create(file=f, purpose="user_data")
            content.append({"type": "input_file", "file_id": uploaded.id})

        next_input: list[dict] = [{"role": "user", "content": content}]
        response = None

        for _ in range(max_tool_iterations):
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

        return (response.output_parsed if response else None), conversation_id

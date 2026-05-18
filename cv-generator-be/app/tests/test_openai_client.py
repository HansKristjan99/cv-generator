"""Live integration tests — require OPENAI_API_KEY and network access."""

from pathlib import Path

from pydantic import BaseModel

from app.services.openai_client import OpenAIClient

MODEL = "gpt-4o-mini"


class Person(BaseModel):
    name: str
    age: int


def test_get_response() -> None:
    client = OpenAIClient(MODEL)
    out = client.get_response("Reply with the single word: pong")
    assert isinstance(out, str)
    assert len(out) > 0


def test_get_structured_output() -> None:
    client = OpenAIClient(MODEL)
    out, _ = client.get_structured_output(
        "Alice is 30 years old. Extract her name and age.",
        Person,
    )
    assert out is not None
    assert out.name.lower() == "alice"
    assert out.age == 30


def test_get_structured_output_with_file(tmp_path: Path) -> None:
    file = tmp_path / "bob.txt"
    file.write_text("Bob is 42 years old.")

    client = OpenAIClient(MODEL)
    out, _ = client.get_structured_output(
        "Extract the person's name and age from the attached file.",
        Person,
        file=file,
    )
    assert out is not None
    assert out.name.lower() == "bob"
    assert out.age == 42

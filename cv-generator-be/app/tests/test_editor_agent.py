"""EditorAgent unit tests covering the structured-output loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from app.agents.editor import EditorAgent
from app.schemas import CurriculumVitae, LayoutOverrides, PolishedCv
from app.services.latex import CompileResult


def _cv(target_pages: int = 1) -> CurriculumVitae:
    return CurriculumVitae(
        name="Test", location="Zürich", email="t@e.com", phone=None, links=[],
        summary="Engineer.", experience=[], education=[], skills=[], projects=[],
        awards=[], job_requirements=[], target_pages=target_pages,
    )


def _layout(font: int = 10, margin: float = 1.2, spacing: int = 8) -> LayoutOverrides:
    return LayoutOverrides(font_size_pt=font, margin_cm=margin, section_spacing_pt=spacing)


@dataclass
class _FakeClient:
    """Stand-in for OpenAIClient. Returns scripted PolishedCv values in order."""

    outputs: list[PolishedCv]
    calls: int = field(default=0)
    last_tools: list | None = field(default=None)

    def get_structured_output(self, prompt, output_structure, **kwargs):  # noqa: ARG002
        self.last_tools = kwargs.get("tools")
        idx = self.calls
        self.calls += 1
        if idx >= len(self.outputs):
            return None, "conv-id"
        return self.outputs[idx], "conv-id"


def test_skips_polish_when_initial_already_fits() -> None:
    client = _FakeClient(outputs=[])
    cv, layout = _cv(), _layout()
    initial = CompileResult(success=True, page_count=1, pdf_bytes=b"PDF")
    with patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        out = EditorAgent(client).run(
            cv=cv, layout=layout, template_slug="default",
            initial_compile=initial, target_pages=1, job_description=None,
        )
    assert out.hit_target is True
    assert out.iterations == 0
    assert client.calls == 0


def test_iterates_until_page_count_hits_target() -> None:
    cv, layout = _cv(), _layout()
    outputs = [PolishedCv(cv=cv, layout=layout), PolishedCv(cv=cv, layout=layout)]
    client = _FakeClient(outputs=outputs)
    initial = CompileResult(success=True, page_count=3, pdf_bytes=b"PDF")
    compiles = [
        CompileResult(success=True, page_count=2, pdf_bytes=b"PDF2"),
        CompileResult(success=True, page_count=1, pdf_bytes=b"PDF3"),
    ]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles), \
         patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        out = EditorAgent(client).run(
            cv=cv, layout=layout, template_slug="default",
            initial_compile=initial, target_pages=1, job_description="JD",
        )
    assert out.hit_target is True
    assert out.page_count == 1
    assert out.iterations == 2


def test_returns_closest_render_after_max_iters() -> None:
    cv, layout = _cv(), _layout()
    outputs = [PolishedCv(cv=cv, layout=layout), PolishedCv(cv=cv, layout=layout)]
    client = _FakeClient(outputs=outputs)
    initial = CompileResult(success=True, page_count=5, pdf_bytes=b"PDF-init")
    compiles = [
        CompileResult(success=True, page_count=3, pdf_bytes=b"PDF-A"),
        CompileResult(success=True, page_count=4, pdf_bytes=b"PDF-B"),
    ]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles), \
         patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        out = EditorAgent(client, max_iterations=2).run(
            cv=cv, layout=layout, template_slug="default",
            initial_compile=initial, target_pages=1, job_description=None,
        )
    assert out.hit_target is False
    assert out.page_count == 3  # closest to target
    assert out.pdf_bytes == b"PDF-A"


def test_falls_back_to_initial_when_polished_never_compiles() -> None:
    cv, layout = _cv(), _layout()
    outputs = [PolishedCv(cv=cv, layout=layout), PolishedCv(cv=cv, layout=layout)]
    client = _FakeClient(outputs=outputs)
    initial = CompileResult(success=True, page_count=3, pdf_bytes=b"PDF")
    compiles = [
        CompileResult(success=False, page_count=0, pdf_bytes=None, error="syntax"),
        CompileResult(success=False, page_count=0, pdf_bytes=None, error="syntax"),
    ]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles), \
         patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        out = EditorAgent(client, max_iterations=2).run(
            cv=cv, layout=layout, template_slug="default",
            initial_compile=initial, target_pages=1, job_description=None,
        )
    assert out.pdf_bytes == b"PDF"  # original initial render
    assert out.hit_target is False


def test_raises_when_no_compile_ever_succeeds() -> None:
    cv, layout = _cv(), _layout()
    outputs = [PolishedCv(cv=cv, layout=layout)]
    client = _FakeClient(outputs=outputs)
    initial = CompileResult(success=False, page_count=0, pdf_bytes=None, error="boom")
    compiles = [CompileResult(success=False, page_count=0, pdf_bytes=None, error="boom")]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles), \
         patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        with pytest.raises(RuntimeError, match="no compiling render"):
            EditorAgent(client, max_iterations=1).run(
                cv=cv, layout=layout, template_slug="default",
                initial_compile=initial, target_pages=1, job_description=None,
            )


def test_profile_tool_exposed_only_when_memory_provider_given() -> None:
    cv, layout = _cv(), _layout()
    client = _FakeClient(outputs=[PolishedCv(cv=cv, layout=layout)])
    initial = CompileResult(success=True, page_count=2, pdf_bytes=b"PDF")
    compiles = [CompileResult(success=True, page_count=1, pdf_bytes=b"PDF2")]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles), \
         patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        EditorAgent(client, max_iterations=1, memory_provider=lambda: "stored profile").run(
            cv=cv, layout=layout, template_slug="default",
            initial_compile=initial, target_pages=1, job_description=None,
        )
    assert client.last_tools is not None
    assert client.last_tools[0]["name"] == "fetch_candidate_profile"


def test_profile_tool_absent_without_memory_provider() -> None:
    cv, layout = _cv(), _layout()
    client = _FakeClient(outputs=[PolishedCv(cv=cv, layout=layout)])
    initial = CompileResult(success=True, page_count=2, pdf_bytes=b"PDF")
    compiles = [CompileResult(success=True, page_count=1, pdf_bytes=b"PDF2")]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles), \
         patch("app.agents.editor.cv_to_latex", return_value="rendered"):
        EditorAgent(client, max_iterations=1).run(
            cv=cv, layout=layout, template_slug="default",
            initial_compile=initial, target_pages=1, job_description=None,
        )
    assert client.last_tools is None


def test_profile_handler_returns_memory_blob() -> None:
    from app.agents.editor import _profile_handler
    handler = _profile_handler(lambda: "stored facts")
    assert handler("fetch_candidate_profile", {"reason": "expand"}) == {"profile": "stored facts"}
    assert handler("fetch_candidate_profile", {"reason": ""}) == {"profile": "stored facts"}


def test_profile_handler_handles_empty_memory() -> None:
    from app.agents.editor import _profile_handler
    handler = _profile_handler(lambda: "")
    assert handler("fetch_candidate_profile", {"reason": "x"}) == {"profile": "(no stored profile)"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

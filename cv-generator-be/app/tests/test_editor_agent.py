"""EditorAgent unit tests: page-count loop, fallback on compile failure, success early-exit."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from app.agents.editor import EditorAgent
from app.schemas import PolishedCv
from app.services.latex import CompileResult


@dataclass
class _FakeClient:
    """Stand-in for OpenAIClient. Returns scripted PolishedCv outputs in order."""

    outputs: list[str]
    calls: int = 0

    def get_structured_output(self, prompt, output_structure, **kwargs):  # noqa: D401, ARG002
        idx = self.calls
        self.calls += 1
        if idx >= len(self.outputs):
            return None, "conv-id"
        return PolishedCv(latex=self.outputs[idx]), "conv-id"


def _compile_results(seq: list[CompileResult]) -> callable:
    it = iter(seq)

    def _fake(latex: str, timeout: float = 25.0):  # noqa: ARG001
        return next(it)

    return _fake


def test_skips_polish_when_initial_already_fits() -> None:
    client = _FakeClient(outputs=[])
    initial = CompileResult(success=True, page_count=1, pdf_bytes=b"PDF")
    out = EditorAgent(client).run(
        latex=r"\documentclass{article}\begin{document}x\end{document}",
        initial_compile=initial, target_pages=1, job_description=None,
    )
    assert out.hit_target is True
    assert out.iterations == 0
    assert client.calls == 0


def test_iterates_until_page_count_hits_target() -> None:
    client = _FakeClient(outputs=["trim-1", "trim-2"])
    initial = CompileResult(success=True, page_count=3, pdf_bytes=b"PDF")
    compiles = [
        CompileResult(success=True, page_count=2, pdf_bytes=b"PDF2"),
        CompileResult(success=True, page_count=1, pdf_bytes=b"PDF3"),
    ]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles):
        out = EditorAgent(client).run(
            latex="orig", initial_compile=initial, target_pages=1, job_description="JD",
        )
    assert out.hit_target is True
    assert out.page_count == 1
    assert out.latex == "trim-2"
    assert out.iterations == 2


def test_returns_smallest_overshoot_after_max_iters() -> None:
    client = _FakeClient(outputs=["v1", "v2"])
    initial = CompileResult(success=True, page_count=5, pdf_bytes=b"PDF")
    compiles = [
        CompileResult(success=True, page_count=3, pdf_bytes=b"PDF-A"),
        CompileResult(success=True, page_count=4, pdf_bytes=b"PDF-B"),
    ]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles):
        out = EditorAgent(client, max_iterations=2).run(
            latex="orig", initial_compile=initial, target_pages=1, job_description=None,
        )
    assert out.hit_target is False
    assert out.page_count == 3
    assert out.latex == "v1"


def test_skips_polish_when_initial_compile_failed() -> None:
    client = _FakeClient(outputs=[])
    initial = CompileResult(success=False, page_count=0, pdf_bytes=None, error="boom")
    out = EditorAgent(client).run(
        latex="orig", initial_compile=initial, target_pages=1, job_description=None,
    )
    assert client.calls == 0
    assert out.latex == "orig"
    assert out.hit_target is False


def test_falls_back_to_original_when_polished_never_compiles() -> None:
    client = _FakeClient(outputs=["bad-1", "bad-2"])
    initial = CompileResult(success=True, page_count=3, pdf_bytes=b"PDF")
    compiles = [
        CompileResult(success=False, page_count=0, pdf_bytes=None, error="syntax"),
        CompileResult(success=False, page_count=0, pdf_bytes=None, error="syntax"),
    ]
    with patch("app.agents.editor.compile_latex_to_pdf", side_effect=compiles):
        out = EditorAgent(client, max_iterations=2).run(
            latex="orig", initial_compile=initial, target_pages=1, job_description=None,
        )
    # No compile succeeded, so we keep the original initial render.
    assert out.latex == "orig"
    assert out.pdf_bytes == b"PDF"
    assert out.hit_target is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

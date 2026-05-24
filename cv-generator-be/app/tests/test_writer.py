"""WriterAgent compile handler: page count is a ceiling, not an exact target."""

import app.agents.writer as writer
from app.services.latex import CompileResult


def _cv_args() -> dict:
    return {
        "name": "Test Person",
        "location": "Zürich, Switzerland",
        "email": "test@example.com",
        "phone": None,
        "links": [],
        "summary": "Engineer.",
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "awards": [],
    }


def _patch_compile(monkeypatch, page_count: int, success: bool = True) -> None:
    monkeypatch.setattr(writer, "cv_to_latex", lambda cv, slug: "LATEX")
    monkeypatch.setattr(
        writer,
        "compile_latex_to_pdf",
        lambda latex: CompileResult(
            success=success,
            page_count=page_count,
            pdf_bytes=b"%PDF" if success else None,
        ),
    )


def test_fits_when_under_ceiling(monkeypatch) -> None:
    _patch_compile(monkeypatch, page_count=1)
    payload, pdf = writer._compile_handler("default", target_pages=2)("compile_cv", _cv_args())
    assert payload["fits_target"] is True
    assert payload["page_count"] == 1
    assert payload["max_pages"] == 2
    assert pdf == b"%PDF"


def test_fits_when_exactly_at_ceiling(monkeypatch) -> None:
    _patch_compile(monkeypatch, page_count=2)
    payload, _ = writer._compile_handler("default", target_pages=2)("compile_cv", _cv_args())
    assert payload["fits_target"] is True


def test_fails_when_over_ceiling(monkeypatch) -> None:
    _patch_compile(monkeypatch, page_count=3)
    payload, _ = writer._compile_handler("default", target_pages=2)("compile_cv", _cv_args())
    assert payload["fits_target"] is False


def test_fails_when_compile_unsuccessful(monkeypatch) -> None:
    _patch_compile(monkeypatch, page_count=0, success=False)
    result = writer._compile_handler("default", target_pages=1)("compile_cv", _cv_args())
    payload = result[0] if isinstance(result, tuple) else result
    assert payload["fits_target"] is False
    assert payload["success"] is False

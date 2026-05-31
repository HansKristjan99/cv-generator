"""Load the frozen eval dataset and recorded fixtures.

Pure I/O over JSON — no network, no agents — so CI can load cases and fixtures
without an API key. The dataset is the human-authored ground truth; treat
``dataset/cases.jsonl`` like test fixtures: version it, grow it deliberately, and
don't tune prompts blindly against it (that's overfitting).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.evals.types import EvalCase, GeneratedCV
from app.schemas import CurriculumVitae

_HERE = Path(__file__).parent
DATASET_PATH = _HERE / "dataset" / "cases.jsonl"
FIXTURES_DIR = _HERE / "fixtures"


def load_cases(path: Path | None = None) -> list[EvalCase]:
    """Read the JSONL dataset into validated :class:`EvalCase` objects."""
    path = path or DATASET_PATH
    cases: list[EvalCase] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(EvalCase.model_validate_json(line))
    return cases


def load_fixture(name: str) -> GeneratedCV:
    """Load a recorded generator output (``fixtures/<name>.json``).

    Fixtures record the structured CV plus the *recorded* compile outcome
    (success + page count), so deterministic evaluators — including ``page_fit`` —
    can run with no LaTeX toolchain. They make the evaluator logic itself testable
    in CI on every push.
    """
    data = json.loads((FIXTURES_DIR / f"{name}.json").read_text())
    return GeneratedCV(
        cv=CurriculumVitae.model_validate(data["cv"]),
        compile_success=data.get("compile_success", False),
        page_count=data.get("page_count", 0),
        metadata=data.get("metadata", {}),
    )

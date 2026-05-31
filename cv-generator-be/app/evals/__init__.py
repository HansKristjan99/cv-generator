"""CV-quality eval harness.

Layers, cheapest first:
  * ``deterministic`` — objective checks (compiles, page-fit, skills evidenced,
    bullets quantified, no self-duplication, must-have coverage). No network, no
    LaTeX toolchain; gated on every push.
  * ``judge`` — LLM-as-judge over a decomposed rubric for the subjective residue,
    plus position-bias-controlled pairwise comparison. Run on demand / nightly.

The system under test is the :class:`~app.evals.types.CVGenerator` protocol, so the
Phase 2 LangGraph critic-loop slots in beside today's writer with no runner changes.
"""

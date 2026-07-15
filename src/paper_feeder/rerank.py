"""Optional LLM rerank seam (off by default).

The core pipeline is keyword-only. This module is the single, isolated place
where an LLM could rerank the top slice of already-keyword-scored records
before rendering. It is a no-op unless ``llm_rerank.enabled`` is true in
``scoring.yaml``, and importing ``anthropic`` is deferred so the base install
never needs it.

Config shape (in scoring.yaml)::

    llm_rerank:
      enabled: false
      model: claude-haiku-4-5
      top_n: 20            # only the top N keyword-scored records are reranked

To implement: send the top-N titles+abstracts to the model with the same
rubric used to compile the lexicon, ask for a 1-5 relevance score + one-line
reason, and blend/override ``record.score`` (and set ``record.matched`` to the
model's reason). Everything below top_n keeps its keyword score untouched.
"""

from __future__ import annotations

from .models import Record


def maybe_rerank(records: list[Record], config: dict) -> list[Record]:
    """Return records unchanged unless the LLM rerank seam is enabled.

    ``records`` are assumed already keyword-scored and sorted best-first.
    """
    cfg = config.get("llm_rerank") or {}
    if not cfg.get("enabled"):
        return records
    raise NotImplementedError(
        "llm_rerank.enabled is true but no reranker is wired up yet. "
        "Implement maybe_rerank() (see module docstring) or set enabled: false."
    )

"""Within-run deduplication by DOI, falling back to a normalized title hash."""

from __future__ import annotations

import hashlib
import re

from .models import Record

_WS = re.compile(r"\s+")
_NONWORD = re.compile(r"[^\w\s]")


def title_hash(title: str) -> str:
    """Stable hash of a normalized title (lowercased, punctuation stripped)."""
    # Punctuation -> space so "Ice-Sheet Dynamics!" and "ice sheet dynamics"
    # collapse to the same key.
    norm = _NONWORD.sub(" ", title.lower())
    norm = _WS.sub(" ", norm).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def dedupe(records: list[Record]) -> list[Record]:
    """Collapse duplicates within a run, preferring the copy with an abstract.

    Records are keyed by DOI when present, otherwise by normalized-title hash.
    """
    best: dict[str, Record] = {}
    for rec in records:
        key = rec.key
        current = best.get(key)
        if current is None:
            best[key] = rec
            continue
        # A paper can arrive from several sources; the surviving copy must keep
        # the strongest source signal any copy carried.
        merged_always = current.always_include or rec.always_include
        merged_boost = max(current.score_boost, rec.score_boost)
        # Prefer a record that carries an abstract over one that doesn't.
        if current.abstract is None and rec.abstract is not None:
            best[key] = rec
        best[key].always_include = merged_always
        best[key].score_boost = merged_boost
    return list(best.values())

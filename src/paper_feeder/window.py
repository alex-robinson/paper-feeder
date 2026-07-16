"""Rolling display window: the full scored records currently shown on the page.

Old papers are never re-fetched (they leave the RSS feed after a few days), so
to keep them on the HTML page for a rolling window we must persist the scored
records themselves — not just their identity keys. ``data/window.json`` holds
the digest records within the window; ``seen.json`` (see ``seen.py``) remains
the tiny key-based dedup ledger that keeps RSS strictly once-per-paper.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Record

_FIELDS = (
    "title", "journal", "source", "url", "doi", "abstract", "authors",
    "is_editorial", "abstract_missing", "always_include", "score", "matched",
)


def to_dict(rec: Record) -> dict:
    d = {f: getattr(rec, f) for f in _FIELDS}
    d["published"] = rec.published.isoformat() if rec.published else None
    d["first_seen"] = rec.first_seen.isoformat() if rec.first_seen else None
    return d


def from_dict(d: dict) -> Record:
    rec = Record(
        title=d.get("title", ""),
        journal=d.get("journal", ""),
        source=d.get("source", ""),
        url=d.get("url", ""),
        doi=d.get("doi"),
        abstract=d.get("abstract"),
        authors=list(d.get("authors") or []),
        is_editorial=bool(d.get("is_editorial")),
        abstract_missing=bool(d.get("abstract_missing")),
        always_include=bool(d.get("always_include")),
        score=float(d.get("score", 0.0)),
        matched=list(d.get("matched") or []),
    )
    rec.published = date.fromisoformat(d["published"]) if d.get("published") else None
    rec.first_seen = (
        date.fromisoformat(d["first_seen"]) if d.get("first_seen") else None
    )
    return rec


def load_window(path: str | Path) -> list[Record]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return [from_dict(d) for d in data] if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError, KeyError, ValueError):
        return []


def save_window(records: list[Record], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = [to_dict(r) for r in records]
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def add_to_window(
    window: list[Record], new_records: list[Record], first_seen: date
) -> list[Record]:
    """Stamp ``first_seen`` on new records and append, deduping by key.

    Existing entries keep their earlier ``first_seen``.
    """
    by_key = {r.key: r for r in window}
    for rec in new_records:
        if rec.key not in by_key:
            rec.first_seen = first_seen
            by_key[rec.key] = rec
    return list(by_key.values())


def prune_window(
    window: list[Record], today: date, window_days: int
) -> list[Record]:
    """Keep records first seen within the last ``window_days``."""
    cutoff = today - timedelta(days=window_days)
    return [r for r in window if r.first_seen and r.first_seen >= cutoff]

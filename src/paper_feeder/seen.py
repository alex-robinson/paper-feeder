"""Committed-state tracking: which records we've already published.

``data/seen.json`` maps an identity key (DOI, or ``title:<hash>``) to the ISO
date we first saw it. Entries older than a retention window are pruned to keep
the file bounded.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Record


def load_seen(path: str | Path) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen(seen: dict[str, str], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys for deterministic diffs in git
    p.write_text(json.dumps(seen, indent=2, sort_keys=True) + "\n")


def filter_unseen(records: list[Record], seen: dict[str, str]) -> list[Record]:
    """Drop records whose identity key is already in ``seen``."""
    return [r for r in records if r.key not in seen]


def update_seen(
    seen: dict[str, str], records: list[Record], run_date: date
) -> dict[str, str]:
    """Record the first-seen date for each processed record (non-destructive)."""
    iso = run_date.isoformat()
    for r in records:
        seen.setdefault(r.key, iso)
    return seen


def prune_seen(
    seen: dict[str, str], run_date: date, retention_days: int = 180
) -> dict[str, str]:
    """Drop entries first seen more than ``retention_days`` ago."""
    cutoff = run_date - timedelta(days=retention_days)
    kept: dict[str, str] = {}
    for key, iso in seen.items():
        try:
            first = date.fromisoformat(iso)
        except (ValueError, TypeError):
            continue  # drop malformed entries
        if first >= cutoff:
            kept[key] = iso
    return kept

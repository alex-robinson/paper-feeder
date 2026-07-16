"""Common record schema shared across every pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Record:
    """One candidate paper, normalized from any source."""

    title: str
    journal: str
    source: str  # e.g. "rss:nature" | "openalex:ice-sheets" | "crossref:1758-678X"
    url: str
    doi: str | None = None  # canonical: lowercase, no https://doi.org/ prefix
    abstract: str | None = None
    authors: list[str] = field(default_factory=list)
    published: date | None = None

    # provenance flags
    is_editorial: bool = False  # News & Views, Perspectives, etc.
    abstract_missing: bool = False
    # Source was marked always_include: keep regardless of score (e.g. a query
    # tracking citations of your own work). Exclusions still veto.
    always_include: bool = False

    # set when a record first enters the rolling display window
    first_seen: date | None = None

    # scoring output
    score: float = 0.0
    matched: list[str] = field(default_factory=list)  # terms that hit, for display
    excluded: bool = False  # vetoed by an exclusion term

    @property
    def key(self) -> str:
        """Stable dedup/identity key: DOI if present, else a normalized title hash."""
        from .dedupe import title_hash

        return self.doi if self.doi else f"title:{title_hash(self.title)}"

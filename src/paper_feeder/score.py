"""Weighted keyword scoring.

The lexicon is compiled occasionally (by hand, with Claude's help) from a
personal library and interests, and lives in ``config/scoring.yaml``. This
module turns that config into compiled regexes and scores each record; it is
pure Python with no network or model dependency.

An ``include`` entry is one of:
    - {term: "ice sheet", weight: 3}   # literal phrase, matched with word
                                        # boundaries; spaces also match hyphens
    - {pattern: "ice[- ]sheet", weight: 3}  # raw regex, used as-is

Scoring, per record:
    score = sum over matching include entries of
        weight * title_boost   if the term appears in the title
      + weight                 if the term appears in the abstract
An entry contributes at most once per field (presence, not frequency).

An ``exclude`` match anywhere (title or abstract) vetoes the record: it is
marked ``excluded`` and kept out of the digest regardless of score. Use
exclusions to suppress known polysemy false positives (e.g. "GIA" in
"Georgia", economic "tipping point").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Record


@dataclass
class _Term:
    label: str  # human-readable, shown in "why it matched"
    regex: re.Pattern
    weight: float


@dataclass
class Lexicon:
    include: list[_Term]
    exclude: list[re.Pattern]
    title_boost: float
    publish_min_score: float


def _term_to_regex(term: str) -> re.Pattern:
    """Literal phrase -> case-insensitive regex with word boundaries.

    Internal whitespace becomes ``[\\s-]+`` so "ice sheet" also matches
    "ice-sheet" and "ice  sheet".
    """
    escaped = re.escape(term.strip())
    escaped = re.sub(r"\\?\s+", r"[\\s-]+", escaped)
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


def compile_lexicon(config: dict) -> Lexicon:
    include: list[_Term] = []
    for entry in config.get("include", []):
        weight = float(entry.get("weight", 1))
        if "pattern" in entry:
            rx = re.compile(entry["pattern"], re.IGNORECASE)
            label = entry.get("label", entry["pattern"])
        else:
            term = entry["term"]
            rx = _term_to_regex(term)
            label = entry.get("label", term)
        include.append(_Term(label=label, regex=rx, weight=weight))

    exclude: list[re.Pattern] = []
    for entry in config.get("exclude", []):
        if isinstance(entry, dict):
            exclude.append(
                re.compile(entry["pattern"], re.IGNORECASE)
                if "pattern" in entry
                else _term_to_regex(entry["term"])
            )
        else:
            exclude.append(_term_to_regex(str(entry)))

    return Lexicon(
        include=include,
        exclude=exclude,
        title_boost=float(config.get("title_boost", 2.0)),
        publish_min_score=float(config.get("publish_min_score", 3.0)),
    )


def score_record(record: Record, lexicon: Lexicon) -> Record:
    """Populate ``score``, ``matched`` and ``excluded`` on the record in place."""
    title = record.title or ""
    abstract = record.abstract or ""

    for rx in lexicon.exclude:
        if rx.search(title) or rx.search(abstract):
            record.excluded = True
            record.score = 0.0
            record.matched = []
            return record

    score = 0.0
    matched: list[str] = []
    for term in lexicon.include:
        hit = False
        if term.regex.search(title):
            score += term.weight * lexicon.title_boost
            hit = True
        if term.regex.search(abstract):
            score += term.weight
            hit = True
        if hit:
            matched.append(term.label)

    # Source-level partial credit (e.g. "cites my work") tops up the keyword
    # score, so such papers still need some topical signal to clear the bar.
    record.score = score + record.score_boost
    record.matched = matched
    record.excluded = False
    return record


def score_records(records: list[Record], config: dict) -> list[Record]:
    """Score every record and return them sorted best-first (excluded dropped)."""
    lexicon = compile_lexicon(config)
    for rec in records:
        score_record(rec, lexicon)
    kept = [r for r in records if not r.excluded]
    kept.sort(key=lambda r: r.score, reverse=True)
    return kept

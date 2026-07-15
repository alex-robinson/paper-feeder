"""RSS/Atom fetching via feedparser.

``parse_feed`` is pure (takes an already-parsed feedparser result), so DOI
extraction and editorial detection are unit-testable without the network.
``fetch_rss`` is the thin networked shell.
"""

from __future__ import annotations

import html as _html
import logging
import re

import feedparser

from ..models import Record
from ..normalize import canonical_doi, parse_date

log = logging.getLogger("paper_feeder.rss")

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _clean_summary(text: str | None) -> str | None:
    """RSS summaries are often HTML; reduce to collapsed plain text."""
    if not text:
        return None
    text = _html.unescape(text)  # reveal any escaped tags first
    text = _TAG.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    return text or None

# Titles/tags that signal editorial (keep, but flag so it can bypass thresholds).
_EDITORIAL_HINTS = (
    "news & views",
    "news and views",
    "perspective",
    "editorial",
    "comment",
    "correspondence",
    "opinion",
)


def _extract_doi(entry) -> str | None:
    """Publishers scatter the DOI across different fields; try each."""
    for field in ("id", "dc_identifier", "prism_doi", "doi"):
        doi = canonical_doi(entry.get(field))
        if doi:
            return doi
    # links (entry.link, entry.links[].href)
    doi = canonical_doi(entry.get("link"))
    if doi:
        return doi
    for link in entry.get("links", []) or []:
        doi = canonical_doi(link.get("href"))
        if doi:
            return doi
    return None


def _is_editorial(entry) -> bool:
    haystacks = [entry.get("title", "")]
    for tag in entry.get("tags", []) or []:
        haystacks.append(tag.get("term", ""))
    blob = " ".join(haystacks).lower()
    return any(hint in blob for hint in _EDITORIAL_HINTS)


def parse_feed(name: str, parsed, journal: str | None = None) -> list[Record]:
    feed_title = getattr(parsed.feed, "title", name) if parsed.feed else name
    records: list[Record] = []
    for entry in parsed.entries:
        abstract = _clean_summary(entry.get("summary"))
        records.append(
            Record(
                title=(entry.get("title") or "").strip(),
                journal=journal or feed_title or name,
                source=f"rss:{name}",
                url=entry.get("link", ""),
                doi=_extract_doi(entry),
                abstract=abstract,
                authors=[
                    a.get("name", "")
                    for a in (entry.get("authors", []) or [])
                    if a.get("name")
                ],
                published=parse_date(entry.get("published_parsed")),
                is_editorial=_is_editorial(entry),
                abstract_missing=abstract is None,
            )
        )
    return records


def fetch_rss(name: str, url: str, journal: str | None = None) -> list[Record]:
    try:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            log.warning("feed %s parse error: %s", name, parsed.bozo_exception)
            return []
        return parse_feed(name, parsed, journal=journal)
    except Exception as exc:  # never let one feed kill the run
        log.warning("feed %s failed: %s", name, exc)
        return []

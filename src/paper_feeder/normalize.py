"""Normalization: canonical DOIs, abstract reconstruction, source -> Record."""

from __future__ import annotations

import re
from datetime import date

from .models import Record

_DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


def canonical_doi(value: str | None) -> str | None:
    """Return a bare lowercase DOI (``10.xxxx/yyyy``) or None.

    Accepts full URLs, ``doi:`` prefixes, or bare DOIs. Strips a trailing
    punctuation that publishers sometimes append in RSS ids.
    """
    if not value:
        return None
    match = _DOI_RE.search(value.strip())
    if not match:
        return None
    doi = match.group(0).rstrip(").,;")
    return doi.lower()


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Rebuild plain text from OpenAlex ``abstract_inverted_index``.

    The index maps each word to the list of positions at which it occurs.
    """
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    if not positions:
        return None
    positions.sort()
    return " ".join(word for _, word in positions)


def parse_date(value) -> date | None:
    """Best-effort date parsing across the formats our sources emit."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    # OpenAlex / Crossref ISO string, e.g. "2024-01-15"
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    # feedparser struct_time
    if hasattr(value, "tm_year"):
        try:
            return date(value.tm_year, value.tm_mon, value.tm_mday)
        except (ValueError, TypeError):
            return None
    # Crossref date-parts: [[2024, 1, 15]]
    if isinstance(value, (list, tuple)) and value:
        parts = value[0] if isinstance(value[0], (list, tuple)) else value
        try:
            y = parts[0]
            m = parts[1] if len(parts) > 1 else 1
            d = parts[2] if len(parts) > 2 else 1
            return date(int(y), int(m), int(d))
        except (ValueError, TypeError, IndexError):
            return None
    return None


def record_from_openalex_work(work: dict, source: str) -> Record:
    """Build a Record from an OpenAlex ``works`` item."""
    doi = canonical_doi(work.get("doi"))
    loc = work.get("primary_location") or {}
    src = loc.get("source") or {}
    journal = src.get("display_name") or "OpenAlex"
    landing = loc.get("landing_page_url")
    url = landing or (f"https://doi.org/{doi}" if doi else work.get("id", ""))
    authors = [
        (a.get("author") or {}).get("display_name", "")
        for a in (work.get("authorships") or [])
    ]
    authors = [a for a in authors if a]
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    return Record(
        title=(work.get("title") or work.get("display_name") or "").strip(),
        journal=journal,
        source=source,
        url=url,
        doi=doi,
        abstract=abstract,
        authors=authors,
        published=parse_date(work.get("publication_date")),
        abstract_missing=abstract is None,
    )


def record_from_crossref_item(item: dict, source: str) -> Record:
    """Build a Record from a Crossref ``works`` item (fallback source)."""
    doi = canonical_doi(item.get("DOI"))
    title_list = item.get("title") or []
    title = (title_list[0] if title_list else "").strip()
    container = item.get("container-title") or []
    journal = container[0] if container else "Crossref"
    url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
    authors = [
        " ".join(p for p in (a.get("given"), a.get("family")) if p)
        for a in (item.get("author") or [])
    ]
    authors = [a for a in authors if a]
    # Crossref abstracts are JATS XML when present; strip tags crudely.
    abstract = item.get("abstract")
    if abstract:
        abstract = re.sub(r"<[^>]+>", "", abstract).strip()
    issued = (item.get("issued") or {}).get("date-parts")
    return Record(
        title=title,
        journal=journal,
        source=source,
        url=url,
        doi=doi,
        abstract=abstract or None,
        authors=authors,
        published=parse_date(issued),
        abstract_missing=not abstract,
    )

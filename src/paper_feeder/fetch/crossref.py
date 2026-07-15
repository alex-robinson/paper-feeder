"""Crossref works fetching (fallback source for journals OpenAlex indexes poorly).

Abstracts are often absent here; that's acceptable for a fallback — such
records get scored on the title alone.
"""

from __future__ import annotations

import logging
from datetime import date

import requests

from ..models import Record
from ..normalize import record_from_crossref_item
from .http import get_json

log = logging.getLogger("paper_feeder.crossref")

WORKS_URL = "https://api.crossref.org/works"


def fetch_issn(
    session: requests.Session,
    issn: str,
    since: date,
    mailto: str | None,
    rows: int = 200,
) -> list[Record]:
    params = {
        "filter": f"from-pub-date:{since.isoformat()},issn:{issn}",
        "rows": rows,
        "select": "DOI,title,container-title,author,abstract,URL,issued",
    }
    if mailto:
        params["mailto"] = mailto
    try:
        data = get_json(session, WORKS_URL, params=params)
        items = (data.get("message") or {}).get("items", [])
        return [record_from_crossref_item(it, f"crossref:{issn}") for it in items]
    except Exception as exc:
        log.warning("crossref issn %s failed: %s", issn, exc)
        return []

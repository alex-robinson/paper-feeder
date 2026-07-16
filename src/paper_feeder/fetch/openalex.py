"""OpenAlex works fetching, with cursor pagination and the polite pool."""

from __future__ import annotations

import logging
from datetime import date

import requests

from ..models import Record
from ..normalize import record_from_openalex_work
from .http import get_json

log = logging.getLogger("paper_feeder.openalex")

WORKS_URL = "https://api.openalex.org/works"


def build_filter(filter_str: str, since: date) -> str:
    """Add the date window and constrain to journal articles.

    ``type:article`` drops datasets, preprints, theses, and repository deposits
    (Zenodo, HAL, university repos) that topic queries otherwise pull in.
    """
    return f"{filter_str},from_publication_date:{since.isoformat()},type:article"


def _fetch(
    session: requests.Session,
    filter_str: str,
    source: str,
    mailto: str | None,
    max_pages: int = 10,
) -> list[Record]:
    records: list[Record] = []
    cursor = "*"
    for _ in range(max_pages):
        params = {
            "filter": filter_str,
            "per-page": 200,
            "cursor": cursor,
        }
        if mailto:
            params["mailto"] = mailto
        data = get_json(session, WORKS_URL, params=params)
        for work in data.get("results", []):
            records.append(record_from_openalex_work(work, source))
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
    return records


def fetch_query(
    session: requests.Session,
    name: str,
    filter_str: str,
    since: date,
    mailto: str | None,
) -> list[Record]:
    full = build_filter(filter_str, since)
    try:
        return _fetch(session, full, f"openalex:{name}", mailto)
    except Exception as exc:
        log.warning("openalex query %s failed: %s", name, exc)
        return []


def fetch_issn(
    session: requests.Session, issn: str, since: date, mailto: str | None
) -> list[Record]:
    filt = f"primary_location.source.issn:{issn}"
    return fetch_query(session, issn, filt, since, mailto)

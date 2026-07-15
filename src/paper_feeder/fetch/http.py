"""Shared HTTP helper: a requests session with retry/backoff and polite pool."""

from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter, Retry

log = logging.getLogger("paper_feeder.http")

USER_AGENT = "paper-feeder/0.1 (https://github.com/; mailto:{mailto})"


def make_session(mailto: str | None = None) -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = USER_AGENT.format(mailto=mailto or "unknown")
    return session


def get_json(session: requests.Session, url: str, params: dict | None = None) -> dict:
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

"""Orchestrator: fetch -> normalize -> dedupe -> filter seen -> score -> render.

Run as ``python -m paper_feeder.main`` or via the ``paper-feeder`` script.
Paths default to the repo layout but can be overridden with env vars for tests.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from datetime import date, timedelta
from pathlib import Path

from .config import load_yaml
from .dedupe import dedupe
from .fetch.crossref import fetch_issn as crossref_issn
from .fetch.http import make_session
from .fetch.openalex import fetch_issn as openalex_issn
from .fetch.openalex import fetch_query as openalex_query
from .fetch.rss import fetch_rss
from .models import Record
from .render import render_html, render_rss
from .rerank import maybe_rerank
from .score import score_records
from .seen import filter_unseen, load_seen, prune_seen, save_seen, update_seen

log = logging.getLogger("paper_feeder")


def fetch_all(sources: dict, since: date) -> list[Record]:
    """Fetch every configured source, logging and skipping failures."""
    mailto = sources.get("mailto")
    records: list[Record] = []

    for feed in sources.get("rss", []) or []:
        records += fetch_rss(feed["name"], feed["url"], feed.get("journal"))

    session = make_session(mailto)
    oa = sources.get("openalex", {}) or {}
    for q in oa.get("queries", []) or []:
        records += openalex_query(session, q["name"], q["filter"], since, mailto)
    for issn in oa.get("issns", []) or []:
        records += openalex_issn(session, issn, since, mailto)

    cr = sources.get("crossref", {}) or {}
    for issn in cr.get("issns", []) or []:
        records += crossref_issn(session, issn, since, mailto)

    return records


def run(
    config_dir: str | Path,
    data_dir: str | Path,
    docs_dir: str | Path,
    today: date | None = None,
) -> dict:
    """Run the full pipeline. Returns a small summary dict for logging/tests."""
    today = today or date.today()
    config_dir, data_dir, docs_dir = Path(config_dir), Path(data_dir), Path(docs_dir)

    sources = load_yaml(config_dir / "sources.yaml")
    scoring = load_yaml(config_dir / "scoring.yaml")
    lookback = int(sources.get("lookback_days", 2))
    since = today - timedelta(days=lookback)

    records = fetch_all(sources, since)
    records = [r for r in records if r.title]
    records = dedupe(records)

    seen_path = data_dir / "seen.json"
    seen = load_seen(seen_path)
    fresh = filter_unseen(records, seen)

    scored = score_records(fresh, scoring)  # excluded dropped, sorted best-first
    min_score = float(scoring.get("publish_min_score", 3.0))

    digest: list[Record] = []
    below: list[Record] = []
    for rec in scored:
        (digest if (rec.score >= min_score or rec.is_editorial) else below).append(rec)

    digest = maybe_rerank(digest, scoring)  # no-op unless llm_rerank.enabled

    n = int(scoring.get("serendipity_count", 3))
    serendipity = random.sample(below, min(n, len(below))) if below else []

    title = sources.get("title", "Paper Feeder")
    link = sources.get("link", "")

    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.html").write_text(
        render_html(digest, serendipity, today, title=title)
    )
    (docs_dir / "feed.xml").write_text(
        render_rss(digest, today, title=title, link=link)
    )

    # Mark everything we processed so it never reappears; prune to bound the file.
    seen = update_seen(seen, fresh, today)
    seen = prune_seen(seen, today, int(sources.get("retention_days", 180)))
    save_seen(seen, seen_path)

    summary = {
        "fetched": len(records),
        "fresh": len(fresh),
        "digest": len(digest),
        "serendipity": len(serendipity),
    }
    log.info("run complete: %s", summary)
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    root = Path(os.environ.get("PAPER_FEEDER_ROOT", "."))
    parser = argparse.ArgumentParser(description="Build the paper digest.")
    parser.add_argument("--config", default=str(root / "config"))
    parser.add_argument("--data", default=str(root / "data"))
    parser.add_argument("--docs", default=str(root / "docs"))
    args = parser.parse_args()
    run(args.config, args.data, args.docs)


if __name__ == "__main__":
    main()

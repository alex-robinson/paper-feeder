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
from .window import add_to_window, load_window, prune_window, save_window

log = logging.getLogger("paper_feeder")


def _mark(records: list[Record], entry: dict) -> list[Record]:
    """Apply a source entry's ``always_include`` / ``score_boost`` to its records."""
    always = bool(entry.get("always_include"))
    boost = float(entry.get("score_boost", 0) or 0)
    if not (always or boost):
        return records
    for rec in records:
        rec.always_include = rec.always_include or always
        rec.score_boost = max(rec.score_boost, boost)
    return records


def fetch_all(sources: dict, today: date) -> list[Record]:
    """Fetch every configured source, logging and skipping failures.

    Each OpenAlex query may override ``lookback_days``: citation queries need a
    far wider window than topic queries, because citations trickle in and are
    indexed late. A wide window is safe — ``seen.json`` stops re-announcements.
    """
    mailto = sources.get("mailto")
    since = today - timedelta(days=int(sources.get("lookback_days", 2)))

    def _since_for(entry: dict) -> date:
        days = entry.get("lookback_days")
        return today - timedelta(days=int(days)) if days else since

    records: list[Record] = []

    for feed in sources.get("rss", []) or []:
        records += _mark(
            fetch_rss(feed["name"], feed["url"], feed.get("journal")), feed
        )

    session = make_session(mailto)
    oa = sources.get("openalex", {}) or {}
    for q in oa.get("queries", []) or []:
        records += _mark(
            openalex_query(session, q["name"], q["filter"], _since_for(q), mailto), q
        )
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
    records = fetch_all(sources, today)
    records = [r for r in records if r.title]
    records = dedupe(records)

    seen_path = data_dir / "seen.json"
    seen = load_seen(seen_path)
    fresh = filter_unseen(records, seen)

    scored = score_records(fresh, scoring)  # fresh only, excluded dropped, best-first
    min_score = float(scoring.get("publish_min_score", 3.0))

    fresh_digest: list[Record] = []
    fresh_below: list[Record] = []
    for rec in scored:
        keep = rec.score >= min_score or rec.is_editorial or rec.always_include
        (fresh_digest if keep else fresh_below).append(rec)

    fresh_digest = maybe_rerank(fresh_digest, scoring)  # no-op unless enabled

    # Rolling window: today's fresh digest joins prior days' still-recent
    # records so the HTML page holds unread papers for ``window_days``.
    window_path = data_dir / "window.json"
    window = load_window(window_path)
    window = add_to_window(window, fresh_digest, today)
    window = prune_window(window, today, int(sources.get("window_days", 7)))
    window.sort(key=lambda r: r.score, reverse=True)
    save_window(window, window_path)

    n = int(scoring.get("serendipity_count", 3))
    serendipity = (
        random.sample(fresh_below, min(n, len(fresh_below))) if fresh_below else []
    )

    title = sources.get("title", "Paper Feeder")
    link = sources.get("link", "")

    # Optional theming: subtitle + extra CSS (inline and/or a file next to config).
    render_cfg = sources.get("render") or {}
    subtitle = render_cfg.get("subtitle")
    extra_css = render_cfg.get("css") or ""
    css_file = render_cfg.get("css_file")
    if css_file:
        css_path = Path(css_file)
        if not css_path.is_absolute():
            css_path = config_dir / css_file
        try:
            extra_css = (extra_css + "\n" + css_path.read_text()).strip()
        except OSError as exc:
            log.warning("render.css_file %s not readable: %s", css_file, exc)
    extra_css = extra_css or None

    docs_dir.mkdir(parents=True, exist_ok=True)
    # HTML shows the whole rolling window; RSS emits only today's fresh papers
    # (once-per-paper — Feedly tracks read/unread from there).
    (docs_dir / "index.html").write_text(
        render_html(window, serendipity, today, title=title,
                    subtitle=subtitle, extra_css=extra_css)
    )
    (docs_dir / "feed.xml").write_text(
        render_rss(fresh_digest, today, title=title, link=link)
    )

    # Mark everything we processed so it never reappears; prune to bound the file.
    seen = update_seen(seen, fresh, today)
    seen = prune_seen(seen, today, int(sources.get("retention_days", 180)))
    save_seen(seen, seen_path)

    summary = {
        "fetched": len(records),
        "fresh": len(fresh),
        "rss": len(fresh_digest),
        "window": len(window),
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

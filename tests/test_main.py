"""Integration test for the rolling-window behavior across days.

Locks the two rules the design turns on:
  * RSS is once-per-paper (Feedly tracks read/unread from there).
  * The HTML page is a rolling window that holds unread papers for window_days.
"""

from datetime import date
from xml.etree import ElementTree as ET

import paper_feeder.main as main_mod
from paper_feeder.main import run
from paper_feeder.models import Record

SOURCES = """
title: Test
window_days: 7
retention_days: 180
"""

SCORING = """
title_boost: 2.0
publish_min_score: 3.0
serendipity_count: 0
include:
  - {term: "ice sheet", weight: 3}
"""


def _rec(doi, n):
    return Record(title=f"ice sheet {n}", journal="TC", source="rss:x",
                  url=f"u{n}", doi=doi)


def _write_config(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(SOURCES)
    (cfg / "scoring.yaml").write_text(SCORING)
    return cfg


def _rss_titles(docs):
    root = ET.parse(docs / "feed.xml").getroot()
    return [i.find("title").text for i in root.findall(".//item")]


def test_rss_once_html_windowed(tmp_path, monkeypatch):
    cfg = _write_config(tmp_path)
    data, docs = tmp_path / "data", tmp_path / "docs"

    batch: list[Record] = []
    monkeypatch.setattr(main_mod, "fetch_all", lambda sources, since: list(batch))

    # Day 1: paper A appears.
    batch[:] = [_rec("10.1/a", "A")]
    run(cfg, data, docs, today=date(2024, 1, 1))
    assert _rss_titles(docs) == ["ice sheet A"]
    html = (docs / "index.html").read_text()
    assert "ice sheet A" in html

    # Day 2: A still in the feed, plus new paper B.
    batch[:] = [_rec("10.1/a", "A"), _rec("10.1/b", "B")]
    run(cfg, data, docs, today=date(2024, 1, 2))
    # RSS emits only the newly-seen paper B (A already emitted).
    assert _rss_titles(docs) == ["ice sheet B"]
    # HTML window holds both.
    html = (docs / "index.html").read_text()
    assert "ice sheet A" in html and "ice sheet B" in html
    assert "(1 new)" in html  # only B is new today

    # Day 10: nothing new; both A and B have aged past the 7-day window.
    batch[:] = []
    run(cfg, data, docs, today=date(2024, 1, 10))
    assert _rss_titles(docs) == []
    html = (docs / "index.html").read_text()
    assert "ice sheet A" not in html and "ice sheet B" not in html
    assert "No matching papers in the window." in html

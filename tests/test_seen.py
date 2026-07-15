from datetime import date

from paper_feeder.models import Record
from paper_feeder.seen import (
    filter_unseen,
    load_seen,
    prune_seen,
    save_seen,
    update_seen,
)


def _rec(doi):
    return Record(title="T", journal="J", source="s", url="", doi=doi)


def test_filter_unseen():
    seen = {"10.1/a": "2024-01-01"}
    recs = [_rec("10.1/a"), _rec("10.1/b")]
    out = filter_unseen(recs, seen)
    assert [r.doi for r in out] == ["10.1/b"]


def test_update_seen_is_non_destructive():
    seen = {"10.1/a": "2024-01-01"}
    update_seen(seen, [_rec("10.1/a"), _rec("10.1/b")], date(2024, 6, 1))
    assert seen["10.1/a"] == "2024-01-01"  # unchanged
    assert seen["10.1/b"] == "2024-06-01"  # added


def test_prune_seen_drops_old():
    seen = {
        "keep": "2024-06-01",
        "old": "2023-01-01",
        "bad": "not-a-date",
    }
    out = prune_seen(seen, date(2024, 6, 15), retention_days=180)
    assert "keep" in out
    assert "old" not in out
    assert "bad" not in out


def test_load_save_roundtrip(tmp_path):
    p = tmp_path / "sub" / "seen.json"
    save_seen({"10.1/a": "2024-01-01"}, p)
    assert load_seen(p) == {"10.1/a": "2024-01-01"}


def test_load_missing_returns_empty(tmp_path):
    assert load_seen(tmp_path / "nope.json") == {}

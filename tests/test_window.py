from datetime import date

from paper_feeder.models import Record
from paper_feeder.window import (
    add_to_window,
    from_dict,
    load_window,
    prune_window,
    save_window,
    to_dict,
)


def _rec(doi, score=5.0):
    return Record(
        title="Ice sheet", journal="TC", source="s", url="u", doi=doi,
        abstract="a", authors=["A. R."], score=score, matched=["ice sheet"],
        published=date(2024, 1, 1),
    )


def test_dict_roundtrip():
    r = _rec("10.1/a")
    r.first_seen = date(2024, 2, 1)
    out = from_dict(to_dict(r))
    assert out.doi == "10.1/a"
    assert out.matched == ["ice sheet"]
    assert out.authors == ["A. R."]
    assert out.published == date(2024, 1, 1)
    assert out.first_seen == date(2024, 2, 1)
    assert out.score == 5.0


def test_add_stamps_first_seen_and_dedups():
    window = []
    window = add_to_window(window, [_rec("10.1/a")], date(2024, 1, 1))
    assert window[0].first_seen == date(2024, 1, 1)
    # re-adding the same key on a later day keeps the earlier first_seen
    window = add_to_window(window, [_rec("10.1/a"), _rec("10.1/b")], date(2024, 1, 5))
    by_key = {r.key: r for r in window}
    assert by_key["10.1/a"].first_seen == date(2024, 1, 1)
    assert by_key["10.1/b"].first_seen == date(2024, 1, 5)


def test_prune_drops_old():
    window = add_to_window([], [_rec("10.1/a")], date(2024, 1, 1))
    window = add_to_window(window, [_rec("10.1/b")], date(2024, 1, 8))
    kept = prune_window(window, date(2024, 1, 10), window_days=7)
    keys = {r.key for r in kept}
    assert keys == {"10.1/b"}  # a is 9 days old, dropped


def test_load_save_roundtrip(tmp_path):
    r = _rec("10.1/a")
    r.first_seen = date(2024, 1, 1)
    p = tmp_path / "window.json"
    save_window([r], p)
    out = load_window(p)
    assert len(out) == 1
    assert out[0].doi == "10.1/a"


def test_load_missing_returns_empty(tmp_path):
    assert load_window(tmp_path / "nope.json") == []


def test_always_include_round_trips():
    r = _rec("10.1/a")
    r.always_include = True
    r.first_seen = date(2024, 1, 1)
    assert from_dict(to_dict(r)).always_include is True

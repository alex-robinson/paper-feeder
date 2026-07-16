from paper_feeder.dedupe import dedupe, title_hash
from paper_feeder.models import Record


def test_title_hash_normalizes():
    assert title_hash("Ice-Sheet Dynamics!") == title_hash("ice sheet dynamics")
    assert title_hash("A") != title_hash("B")


def test_dedupe_by_doi_prefers_abstract():
    a = Record(title="T", journal="J", source="rss:x", url="", doi="10.1/x")
    b = Record(
        title="T", journal="J", source="openalex:y", url="", doi="10.1/x",
        abstract="has abstract",
    )
    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0].abstract == "has abstract"


def test_dedupe_keeps_first_when_both_have_abstract():
    a = Record(title="T", journal="J", source="s", url="", doi="10.1/x", abstract="a")
    b = Record(title="T", journal="J", source="s", url="", doi="10.1/x", abstract="b")
    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0].abstract == "a"


def test_dedupe_doiless_by_title():
    a = Record(title="Same Title", journal="J", source="s", url="u1")
    b = Record(title="same  title", journal="J", source="s", url="u2")
    c = Record(title="Different", journal="J", source="s", url="u3")
    out = dedupe([a, b, c])
    assert len(out) == 2


def test_dedupe_distinct_dois_kept():
    a = Record(title="T", journal="J", source="s", url="", doi="10.1/a")
    b = Record(title="T", journal="J", source="s", url="", doi="10.1/b")
    assert len(dedupe([a, b])) == 2


def test_dedupe_preserves_always_include_from_any_copy():
    a = Record(title="T", journal="J", source="rss:nature", url="", doi="10.1/x",
               abstract="a")  # no flag, has abstract
    b = Record(title="T", journal="J", source="openalex:cites-me", url="",
               doi="10.1/x", always_include=True)
    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0].always_include is True  # flag survives even though a won


def test_dedupe_keeps_strongest_score_boost():
    a = Record(title="T", journal="J", source="rss:nature", url="", doi="10.1/x",
               abstract="a")
    b = Record(title="T", journal="J", source="openalex:cites-me", url="",
               doi="10.1/x", score_boost=2.0)
    out = dedupe([a, b])
    assert out[0].score_boost == 2.0

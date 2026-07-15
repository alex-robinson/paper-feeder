from paper_feeder.models import Record
from paper_feeder.score import compile_lexicon, score_record, score_records

CONFIG = {
    "title_boost": 2.0,
    "publish_min_score": 3.0,
    "include": [
        {"term": "ice sheet", "weight": 3},
        {"term": "glacial isostatic adjustment", "weight": 5},
        {"pattern": r"\bGIA\b", "weight": 4, "label": "GIA"},
        {"term": "sea-level rise", "weight": 2},
    ],
    "exclude": ["Georgia", "gene"],
}


def _rec(title="", abstract=""):
    return Record(title=title, journal="J", source="s", url="", abstract=abstract)


def test_abstract_match_uses_base_weight():
    lex = compile_lexicon(CONFIG)
    rec = score_record(_rec(abstract="This studies the ice sheet."), lex)
    assert rec.score == 3.0
    assert rec.matched == ["ice sheet"]


def test_title_match_gets_boost():
    lex = compile_lexicon(CONFIG)
    rec = score_record(_rec(title="The ice sheet"), lex)
    assert rec.score == 6.0  # 3 * title_boost(2)


def test_title_and_abstract_stack():
    lex = compile_lexicon(CONFIG)
    rec = score_record(_rec(title="ice sheet", abstract="ice sheet again"), lex)
    assert rec.score == 9.0  # 3*2 (title) + 3 (abstract)


def test_hyphen_and_whitespace_variants_match():
    lex = compile_lexicon(CONFIG)
    assert score_record(_rec(abstract="the ice-sheet model"), lex).score == 3.0
    assert score_record(_rec(abstract="the ice  sheet model"), lex).score == 3.0


def test_word_boundary_gia():
    lex = compile_lexicon(CONFIG)
    # standalone acronym matches
    assert score_record(_rec(abstract="we model GIA effects"), lex).score == 4.0
    # embedded in another word does not
    assert score_record(_rec(abstract="the regional pattern"), lex).score == 0.0


def test_exclude_vetoes():
    lex = compile_lexicon(CONFIG)
    rec = score_record(_rec(title="ice sheet", abstract="in Georgia"), lex)
    assert rec.excluded is True
    assert rec.score == 0.0
    assert rec.matched == []


def test_score_records_sorts_and_drops_excluded():
    recs = [
        _rec(title="ice sheet"),  # 6.0
        _rec(abstract="glacial isostatic adjustment"),  # 5.0
        _rec(title="ice sheet", abstract="gene therapy"),  # excluded
        _rec(abstract="nothing relevant"),  # 0.0
    ]
    out = score_records(recs, CONFIG)
    assert len(out) == 3  # excluded dropped
    assert [round(r.score, 1) for r in out] == [6.0, 5.0, 0.0]

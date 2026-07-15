from datetime import date

from paper_feeder.normalize import (
    canonical_doi,
    parse_date,
    reconstruct_abstract,
    record_from_crossref_item,
    record_from_openalex_work,
)


def test_canonical_doi_variants():
    assert canonical_doi("https://doi.org/10.1038/s41586-024-01234-5") == (
        "10.1038/s41586-024-01234-5"
    )
    assert canonical_doi("doi:10.1038/ABC.123") == "10.1038/abc.123"
    assert canonical_doi("10.5194/tc-18-1-2024") == "10.5194/tc-18-1-2024"
    # trailing punctuation from RSS ids is stripped
    assert canonical_doi("(10.1038/xyz).") == "10.1038/xyz"


def test_canonical_doi_none_and_junk():
    assert canonical_doi(None) is None
    assert canonical_doi("") is None
    assert canonical_doi("no doi here") is None


def test_reconstruct_abstract_orders_by_position():
    inv = {"Ice": [0, 3], "sheets": [1], "melt": [2]}
    assert reconstruct_abstract(inv) == "Ice sheets melt Ice"
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


def test_parse_date_formats():
    assert parse_date("2024-01-15") == date(2024, 1, 15)
    assert parse_date("2024-01-15T09:00:00") == date(2024, 1, 15)
    assert parse_date([[2024, 1, 15]]) == date(2024, 1, 15)
    assert parse_date([[2024]]) == date(2024, 1, 1)
    assert parse_date(None) is None
    assert parse_date("garbage") is None


def test_parse_date_struct_time():
    import time

    st = time.struct_time((2024, 3, 2, 0, 0, 0, 0, 0, 0))
    assert parse_date(st) == date(2024, 3, 2)


def test_record_from_openalex_work():
    work = {
        "doi": "https://doi.org/10.1234/abc",
        "title": "Marine ice sheet instability",
        "publication_date": "2024-02-01",
        "primary_location": {
            "landing_page_url": "https://example.org/abc",
            "source": {"display_name": "The Cryosphere"},
        },
        "authorships": [
            {"author": {"display_name": "A. Robinson"}},
            {"author": {"display_name": "B. Coauthor"}},
        ],
        "abstract_inverted_index": {"Grounding": [0], "line": [1], "retreat": [2]},
    }
    rec = record_from_openalex_work(work, "openalex:ice-sheets")
    assert rec.doi == "10.1234/abc"
    assert rec.title == "Marine ice sheet instability"
    assert rec.journal == "The Cryosphere"
    assert rec.url == "https://example.org/abc"
    assert rec.authors == ["A. Robinson", "B. Coauthor"]
    assert rec.abstract == "Grounding line retreat"
    assert rec.abstract_missing is False
    assert rec.published == date(2024, 2, 1)


def test_record_from_openalex_missing_abstract_flags():
    rec = record_from_openalex_work({"title": "X", "doi": "10.1/x"}, "openalex:q")
    assert rec.abstract is None
    assert rec.abstract_missing is True


def test_record_from_crossref_item_strips_jats():
    item = {
        "DOI": "10.5194/tc-18-1-2024",
        "title": ["Subglacial hydrology"],
        "container-title": ["The Cryosphere"],
        "author": [{"given": "A.", "family": "Robinson"}],
        "abstract": "<jats:p>Water flows <jats:italic>fast</jats:italic>.</jats:p>",
        "URL": "https://doi.org/10.5194/tc-18-1-2024",
        "issued": {"date-parts": [[2024, 1, 1]]},
    }
    rec = record_from_crossref_item(item, "crossref:1234")
    assert rec.doi == "10.5194/tc-18-1-2024"
    assert rec.title == "Subglacial hydrology"
    assert rec.journal == "The Cryosphere"
    assert rec.authors == ["A. Robinson"]
    assert rec.abstract == "Water flows fast."
    assert rec.published == date(2024, 1, 1)

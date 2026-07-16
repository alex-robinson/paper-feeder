from datetime import date

from paper_feeder.fetch.openalex import build_filter


def test_build_filter_adds_date_and_article_type():
    f = build_filter("primary_topic.id:T10644", date(2024, 3, 1))
    assert f == "primary_topic.id:T10644,from_publication_date:2024-03-01,type:article"


def test_build_filter_works_for_issn_pulls():
    f = build_filter("primary_location.source.issn:0022-1430", date(2024, 3, 1))
    assert f.endswith(",type:article")
    assert "from_publication_date:2024-03-01" in f

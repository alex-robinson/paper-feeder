import feedparser

from paper_feeder.fetch.rss import _clean_authors, _copernicus_byline, parse_feed

FEED = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>The Cryosphere Recent</title>
    <item>
      <title>Grounding line retreat in West Antarctica</title>
      <link>https://tc.copernicus.org/articles/18/1/2024/</link>
      <guid>https://doi.org/10.5194/tc-18-1-2024</guid>
      <summary>We model ice sheet retreat.</summary>
      <pubDate>Mon, 15 Jan 2024 00:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Perspective: the future of ice-sheet modelling</title>
      <link>https://tc.copernicus.org/articles/18/2/2024/</link>
      <guid>10.5194/tc-18-2-2024</guid>
    </item>
  </channel>
</rss>
"""


def test_parse_feed_extracts_doi_from_guid():
    parsed = feedparser.parse(FEED)
    recs = parse_feed("tc", parsed, journal="The Cryosphere")
    assert len(recs) == 2
    r0 = recs[0]
    assert r0.doi == "10.5194/tc-18-1-2024"
    assert r0.title == "Grounding line retreat in West Antarctica"
    assert r0.journal == "The Cryosphere"
    assert r0.source == "rss:tc"
    assert r0.abstract == "We model ice sheet retreat."
    assert r0.published is not None
    assert r0.is_editorial is False


def test_parse_feed_detects_editorial_and_bare_doi():
    parsed = feedparser.parse(FEED)
    recs = parse_feed("tc", parsed)
    r1 = recs[1]
    assert r1.doi == "10.5194/tc-18-2-2024"
    assert r1.is_editorial is True  # "Perspective:" in title
    assert r1.abstract_missing is True


def test_clean_authors_splits_wiley_blob():
    # AGU/Wiley return every author as one newline-joined string.
    blob = "Cong Li, \nSusan L. Beck, \nJonathan R. Delph, \nAnne Meltzer"
    assert _clean_authors([blob]) == [
        "Cong Li", "Susan L. Beck", "Jonathan R. Delph", "Anne Meltzer"
    ]
    # one-name-per-entry (Nature) passes through cleanly
    assert _clean_authors(["Andrew Mitchinson"]) == ["Andrew Mitchinson"]
    assert _clean_authors([""]) == []


# Copernicus summary layout: title / authors / citation / abstract, <br>-joined.
_COP_SUMMARY = (
    "<b>Temperature-driven shrinkage of a Himalayan glacier</b><br />\n"
    "Koji Fujita and Rijan B. Kayastha<br />\n"
    "The Cryosphere, 20, 4005–4015, https://doi.org/10.5194/tc-20-4005-2026, 2026<br />\n"
    "We measure the glacier and find it is shrinking fast."
)


def test_copernicus_byline_extracts_authors_and_abstract():
    authors, abstract = _copernicus_byline(_COP_SUMMARY)
    assert authors == ["Koji Fujita", "Rijan B. Kayastha"]
    assert abstract == "We measure the glacier and find it is shrinking fast."
    # title/authors/citation are NOT left in the abstract
    assert "Fujita" not in abstract and "doi.org" not in abstract


def test_copernicus_byline_ignores_non_copernicus_summary():
    # A plain summary (no citation line) must not be misparsed.
    assert _copernicus_byline("Just a normal abstract.") == ([], None)
    assert _copernicus_byline(None) == ([], None)


def test_parse_feed_recovers_copernicus_authors():
    feed = f"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>The Cryosphere</title>
      <item>
        <title>Temperature-driven shrinkage of a Himalayan glacier</title>
        <link>https://tc.copernicus.org/articles/20/4005/2026/</link>
        <guid>10.5194/tc-20-4005-2026</guid>
        <description>{_COP_SUMMARY.replace('<', '&lt;').replace('>', '&gt;')}</description>
      </item></channel></rss>"""
    recs = parse_feed("tc", feedparser.parse(feed), journal="The Cryosphere")
    r = recs[0]
    assert r.authors == ["Koji Fujita", "Rijan B. Kayastha"]
    assert r.abstract == "We measure the glacier and find it is shrinking fast."

import feedparser

from paper_feeder.fetch.rss import parse_feed

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

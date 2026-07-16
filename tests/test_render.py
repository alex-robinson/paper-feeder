from datetime import date
from xml.etree import ElementTree as ET

from paper_feeder.models import Record
from paper_feeder.render import render_html, render_rss


def _rec(**kw):
    base = dict(title="Ice sheet dynamics", journal="The Cryosphere", source="s",
                url="https://example.org/x", doi="10.1/x")
    base.update(kw)
    return Record(**base)


def test_render_html_contains_core_fields():
    rec = _rec(matched=["ice sheet"], score=6.0, abstract="Grounding line retreat.",
               authors=["A. Robinson"], published=date(2024, 2, 1))
    html = render_html([rec], [], date(2024, 2, 2), title="Paper Feeder")
    assert "Paper Feeder" in html
    assert "Ice sheet dynamics" in html
    assert "https://doi.org/10.1/x" in html
    assert "matched: ice sheet" in html
    assert "Grounding line retreat." in html
    assert "A. Robinson" in html


def test_render_html_escapes():
    rec = _rec(title="A <b>bold</b> & tricky title", doi=None,
               url="https://example.org/x")
    html = render_html([rec], [], date(2024, 2, 2))
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_render_html_subtitle_and_extra_css():
    css = ":root { --accent: #06c; }"
    html = render_html([_rec(matched=["ice sheet"], score=6.0)], [],
                       date(2024, 2, 2), subtitle="my digest", extra_css=css)
    assert '<p class="subtitle">my digest</p>' in html
    # extra css is appended after the built-in stylesheet (so it overrides)
    assert css in html
    assert html.index("--accent: #2a7") < html.index(css)


def test_render_html_no_subtitle_by_default():
    html = render_html([_rec()], [], date(2024, 2, 2))
    assert 'class="subtitle"' not in html


def test_render_html_layout():
    import re
    rec = _rec(matched=["ice sheet"], score=6.0, published=date(2024, 2, 1))
    rec.first_seen = date(2024, 2, 2)
    html = render_html([rec], [], date(2024, 2, 2))
    # links open in a new tab
    assert 'target="_blank"' in html and 'rel="noopener noreferrer"' in html
    # title line carries neither the score nor the "new" badge (title never offset)
    h2 = re.search(r"<h2>.*?</h2>", html).group(0)
    assert "6.0" not in h2 and "new" not in h2
    # score sits before "matched:" on the why line
    why = re.search(r'<div class="why">(.*?)</div>', html).group(1)
    assert why.index("6.0") < why.index("matched:")
    # "new" badge sits on the meta line, to the right of the date
    metas = re.findall(r'<div class="meta">(.*?)</div>', html)
    assert any("new" in m and "2024-02-01" in m for m in metas)


def test_render_html_empty_digest():
    html = render_html([], [], date(2024, 2, 2))
    assert "No matching papers in the window." in html


def test_render_html_serendipity_section():
    rec = _rec()
    html = render_html([], [rec], date(2024, 2, 2))
    assert "Serendipity" in html


def test_render_rss_is_wellformed():
    rec = _rec(matched=["ice sheet"], abstract="An abstract.",
               published=date(2024, 2, 1))
    xml = render_rss([rec], date(2024, 2, 2), title="Paper Feeder",
                     link="https://example.org")
    root = ET.fromstring(xml)  # raises if malformed
    assert root.tag == "rss"
    channel = root.find("channel")
    items = channel.findall("item")
    assert len(items) == 1
    assert items[0].find("title").text == "Ice sheet dynamics"
    assert items[0].find("guid").text == "10.1/x"
    assert "matched: ice sheet" in items[0].find("description").text


def test_render_rss_handles_special_chars():
    rec = _rec(title="A & B < C", abstract="x < y & z")
    xml = render_rss([rec], date(2024, 2, 2))
    root = ET.fromstring(xml)  # must not blow up on raw & <
    item = root.find("channel").find("item")
    assert item.find("title").text == "A & B < C"

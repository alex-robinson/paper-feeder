"""Render the digest as a self-contained HTML page and an RSS 2.0 feed.

Both are produced with the standard library only (``html`` + ``xml.etree``);
no templating engine or feed library.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from html import escape
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

from .models import Record

_STYLE = """
:root { color-scheme: light dark; }
body { font: 16px/1.5 -apple-system, system-ui, sans-serif; max-width: 46rem;
       margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 1.5rem; }
.meta { color: #888; font-size: 0.85rem; }
article { border-top: 1px solid #8884; padding: 0.8rem 0; }
article h2 { font-size: 1.05rem; margin: 0 0 0.2rem; }
a { color: inherit; }
.why { color: #2a7; font-size: 0.85rem; }
.score { color: #888; font-variant-numeric: tabular-nums; }
.editorial { color: #a70; }
details summary { cursor: pointer; color: #888; font-size: 0.85rem; }
details p { color: #ccc9; font-size: 0.92rem; }
.section-note { color: #888; font-size: 0.85rem; font-style: italic; }
"""


def _authors_str(authors: list[str], limit: int = 6) -> str:
    if not authors:
        return ""
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + f", … (+{len(authors) - limit})"


def _article_html(rec: Record) -> str:
    href = (
        f"https://doi.org/{rec.doi}"
        if rec.doi
        else escape(rec.url or "#", quote=True)
    )
    title = escape(rec.title or "(untitled)")
    bits = []
    if rec.journal:
        bits.append(escape(rec.journal))
    if rec.published:
        bits.append(rec.published.isoformat())
    if rec.is_editorial:
        bits.append('<span class="editorial">editorial</span>')
    meta = " · ".join(bits)
    authors_line = (
        f'<div class="meta">{escape(_authors_str(rec.authors))}</div>'
        if rec.authors
        else ""
    )
    why = (
        f'<div class="why">matched: {escape(", ".join(rec.matched))}</div>'
        if rec.matched
        else ""
    )
    score = f'<span class="score">{rec.score:.1f}</span>' if rec.score else ""
    abstract = ""
    if rec.abstract:
        abstract = (
            "<details><summary>abstract</summary>"
            f"<p>{escape(rec.abstract)}</p></details>"
        )
    elif rec.abstract_missing:
        abstract = '<div class="section-note">no abstract available</div>'
    return (
        "<article>"
        f'<h2><a href="{href}">{title}</a> {score}</h2>'
        f"{authors_line}"
        f'<div class="meta">{meta}</div>'
        f"{why}{abstract}"
        "</article>"
    )


def render_html(
    digest: list[Record],
    serendipity: list[Record],
    generated_on: date,
    title: str = "Paper Feeder",
) -> str:
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        '<meta name=viewport content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head><body>",
        f"<h1>{escape(title)}</h1>",
        f'<p class="meta">{len(digest)} papers · generated {generated_on.isoformat()}</p>',
    ]
    if digest:
        parts.extend(_article_html(r) for r in digest)
    else:
        parts.append('<p class="section-note">No new matching papers today.</p>')
    if serendipity:
        parts.append(
            '<h1>Serendipity</h1><p class="section-note">'
            "Random below-threshold papers, unscored — a guard against the "
            "filter narrowing the field of view.</p>"
        )
        parts.extend(_article_html(r) for r in serendipity)
    parts.append("</body></html>")
    return "".join(parts)


def render_rss(
    items: list[Record],
    generated_on: date,
    title: str = "Paper Feeder",
    link: str = "",
    description: str = "Keyword-scored digest of new papers.",
) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "lastBuildDate").text = _rfc822(generated_on)

    for rec in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = rec.title or "(untitled)"
        item_link = f"https://doi.org/{rec.doi}" if rec.doi else rec.url
        ET.SubElement(item, "link").text = item_link
        guid = ET.SubElement(item, "guid")
        guid.text = rec.doi or item_link
        guid.set("isPermaLink", "false")
        if rec.published:
            ET.SubElement(item, "pubDate").text = _rfc822(rec.published)
        desc_bits = []
        if rec.matched:
            desc_bits.append("matched: " + ", ".join(rec.matched))
        if rec.abstract:
            desc_bits.append(rec.abstract)
        ET.SubElement(item, "description").text = xml_escape("\n\n".join(desc_bits))

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        rss, encoding="unicode"
    )


def _rfc822(d: date) -> str:
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

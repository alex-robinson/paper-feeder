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

# Themeable via CSS custom properties: a consumer can override any of these by
# passing extra CSS (see render config), e.g. `:root { --accent: #06c; }`.
_STYLE = """
:root {
  color-scheme: light dark;
  --maxw: 52rem;           /* content width */
  --font: 16px/1.5 -apple-system, system-ui, sans-serif;
  --accent: #2a7;          /* "matched" text + "new" badge */
  --muted: #888;           /* meta / secondary text */
  --title-size: 0.85rem;   /* same as meta; bold + link keeps it distinct */
  --title-dark: #b5b5b5;   /* article title colour in dark mode */
}
body { font: var(--font); max-width: var(--maxw); margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 1.5rem; }
.subtitle { color: var(--muted); margin: -0.4rem 0 1rem; }
.meta { color: var(--muted); font-size: 0.85rem; }
article { border-top: 1px solid #8884; padding: 0.8rem 0; }
article h2 { font-size: var(--title-size); margin: 0 0 0.2rem; }
a { color: inherit; }
article h2 a { color: inherit; }
@media (prefers-color-scheme: dark) { article h2 a { color: var(--title-dark); } }
.why { color: var(--accent); font-size: 0.85rem; }
.score { color: var(--muted); font-variant-numeric: tabular-nums; }
.editorial { color: #a70; }
.pin { color: var(--accent); }
.new { background: var(--accent); color: #fff; font-size: 0.7rem; font-weight: 600;
       padding: 0.05rem 0.35rem; border-radius: 0.6rem; vertical-align: middle; }
details summary { cursor: pointer; color: var(--muted); font-size: 0.85rem; }
details p { color: #ccc9; font-size: 0.92rem; }
.section-note { color: var(--muted); font-size: 0.85rem; font-style: italic; }
"""


def _authors_str(authors: list[str], limit: int = 6) -> str:
    if not authors:
        return ""
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + f", … (+{len(authors) - limit})"


def _article_html(rec: Record, today: date | None = None) -> str:
    href = (
        f"https://doi.org/{rec.doi}"
        if rec.doi
        else escape(rec.url or "#", quote=True)
    )
    title = escape(rec.title or "(untitled)")
    new_badge = (
        '<span class="new">new</span>'
        if today is not None and rec.first_seen == today
        else ""
    )
    bits = []
    if rec.journal:
        bits.append(escape(rec.journal))
    if rec.published:
        bits.append(rec.published.isoformat())
    if rec.is_editorial:
        bits.append('<span class="editorial">editorial</span>')
    if rec.always_include:
        # say why a paper is here when its score alone wouldn't have kept it
        label = rec.source.split(":", 1)[-1] or "pinned"
        bits.append(f'<span class="pin">{escape(label)}</span>')
    meta = " · ".join(bits)
    if new_badge:  # "new" sits to the right of the date, off the title line
        meta = f"{meta} {new_badge}" if meta else new_badge
    authors_line = (
        f'<div class="meta">{escape(_authors_str(rec.authors))}</div>'
        if rec.authors
        else ""
    )
    # score sits to the left of "matched:" — both relate to scoring
    score_span = f'<span class="score">{rec.score:.1f}</span>' if rec.score else ""
    matched_txt = (
        f'matched: {escape(", ".join(rec.matched))}' if rec.matched else ""
    )
    why_inner = " ".join(p for p in (score_span, matched_txt) if p)
    why = f'<div class="why">{why_inner}</div>' if why_inner else ""
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
        f'<h2><a href="{href}" target="_blank" rel="noopener noreferrer">{title}</a></h2>'
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
    subtitle: str | None = None,
    extra_css: str | None = None,
) -> str:
    """Render the digest page.

    ``extra_css`` is appended after the built-in stylesheet, so a consumer can
    override the ``:root`` custom properties (or any rule) without editing the
    package. ``subtitle`` renders one line under the title.
    """
    n_new = sum(1 for r in digest if r.first_seen == generated_on)
    style = _STYLE + (extra_css or "")
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        '<meta name=viewport content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title><style>{style}</style></head><body>",
        f"<h1>{escape(title)}</h1>",
        (f'<p class="subtitle">{escape(subtitle)}</p>' if subtitle else ""),
        f'<p class="meta">{len(digest)} papers ({n_new} new) · '
        f"generated {generated_on.isoformat()}</p>",
    ]
    if digest:
        parts.extend(_article_html(r, today=generated_on) for r in digest)
    else:
        parts.append('<p class="section-note">No matching papers in the window.</p>')
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

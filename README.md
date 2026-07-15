# paper-feeder

A daily job that ingests journal RSS feeds + OpenAlex/Crossref queries,
deduplicates by DOI, scores each paper against a **weighted keyword lexicon**,
and publishes a static HTML digest + RSS feed to GitHub Pages.

The daily job is **pure Python — no LLM, no API key**. An LLM is used only
occasionally and interactively (via Claude Code) to compile and refine the
lexicon in [`config/scoring.yaml`](config/scoring.yaml). An optional LLM-rerank
seam exists but is off by default.

## Pipeline

```
fetch (RSS + OpenAlex + Crossref)
  → normalize (canonical DOI, reconstruct OpenAlex abstracts)
  → dedupe (by DOI, else normalized-title hash)
  → filter already-seen (data/seen.json)
  → score (weighted keyword lexicon, title-boosted; exclusions veto)
  → render (docs/index.html + docs/feed.xml)
```

## Layout

```
config/sources.yaml    # RSS feeds + OpenAlex/Crossref queries
config/scoring.yaml    # the weighted lexicon (the heart of the filter)
src/paper_feeder/      # the package
  fetch/               # rss, openalex, crossref (each logs+skips on failure)
  score.py             # keyword scorer
  rerank.py            # optional LLM rerank seam (off by default)
  render.py            # HTML + RSS (stdlib only)
  window.py            # rolling display-window record store
  main.py              # orchestrator
data/seen.json         # dedup ledger: DOI/title -> first-seen date
data/window.json       # scored records currently shown on the page
docs/                  # GitHub Pages root (index.html, feed.xml)
```

## Run locally

```sh
pip install -e ".[dev]"
python -m paper_feeder.main          # writes docs/ and data/seen.json
pytest                                # run tests
```

Paths can be overridden: `python -m paper_feeder.main --config … --data … --docs …`.

## Deploy

GitHub Actions ([`.github/workflows/scan.yml`](.github/workflows/scan.yml)) runs
daily, commits the updated `docs/` and `data/`, and pushes. Point GitHub Pages
at the `main` branch `/docs` folder. **No secrets are required** — the polite-pool
`mailto` in `sources.yaml` is public, and the commit-back uses the default
`GITHUB_TOKEN`.

## Refining the lexicon

`config/scoring.yaml` is the quality lever. Each `include` entry is a literal
phrase (`{term: ..., weight: N}`) or raw regex (`{pattern: ..., weight: N}`);
`exclude` entries veto known false positives. A term in the **title** counts
`title_boost`× its weight; in the abstract, ×1.

Tuning loop: review the digest, note false positives/negatives, and periodically
refine the lexicon. This is transparent and cheap — you can always see exactly
why a paper matched.

The easiest way to refine it is the **`/compile-lexicon` Claude Code command**
([`.claude/commands/compile-lexicon.md`](.claude/commands/compile-lexicon.md)).
Drop your BibTeX library at `seeds/library.bib` and run, inside Claude Code:

```
/compile-lexicon seeds/library.bib notes.txt https://your-group.edu/research
```

It reads those sources, proposes weighted additions/exclusions against the
current `scoring.yaml`, and waits for you to approve before editing. It runs on
your Claude subscription — no API key.

## Reading model: seen vs. unread

Two notions of "seen" live in different places:

- **Emitted** — the scanner has surfaced a paper before. Tracked by
  `data/seen.json` (keyed by DOI), so each paper is announced exactly once and
  never duplicated.
- **Read** — you actually read it. The scanner can't know this; your reader does.

**RSS / Feedly is the read/unread queue.** Each paper enters the feed once with
its DOI as a stable `guid`, stays unread in Feedly until you read it, and can be
reopened later. That's the surface for "came up, didn't read, open again later."

**The HTML page is a rolling `window_days` (default 7) window.** It shows all
matched papers from the last week, relevance-ranked, with a "new" badge on
today's. Unread papers linger on the page for the window, then age out (they
remain in Feedly). RSS stays strictly once-per-paper so Feedly isn't re-spammed.

## Optional LLM rerank

Set `llm_rerank.enabled: true` in `scoring.yaml` and implement
`maybe_rerank()` in [`src/paper_feeder/rerank.py`](src/paper_feeder/rerank.py)
to rerank the top-N keyword-scored papers with a model. Requires the `llm`
extra (`pip install -e ".[llm]"`) and an API key. Left unimplemented by design.

# paper-feeder

A small, installable package that turns journal RSS feeds + OpenAlex/Crossref
queries into a **keyword-scored digest**, published as a static HTML page and an
RSS feed. Point it at your feeds and a weighted keyword lexicon; it fetches,
deduplicates by DOI, scores, and writes `index.html` + `feed.xml`.

The daily job is **pure Python — no LLM, no API key**. An LLM is used only
occasionally and interactively (via the bundled `/compile-lexicon` Claude Code
command) to refine the lexicon. An optional LLM-rerank seam exists, off by default.

**paper-feeder doesn't host anything itself** — you host it in your own repo
(e.g. your GitHub Pages site), holding your own config, state, and output. Anyone
can run their own.

## Host your own — step by step

You need a GitHub repo with GitHub Pages (a `you.github.io` site, or any repo
with Pages on). No API key, no secrets, no server.

**1. Drop the template into your Pages repo root.** From the root of that repo:

```sh
git clone --depth 1 https://github.com/alex-robinson/paper-feeder /tmp/pf
cp -R /tmp/pf/examples/consumer/. .    # copies config/, .github/, .claude/, seeds/
```

**2. Edit `config/sources.yaml`** — your feeds and OpenAlex queries, your polite-pool
`mailto`, and set `link:` to your digest URL (`https://you.github.io/feed/`).

**3. Edit `config/scoring.yaml`** — the weighted keyword lexicon. Start from the
sample and tune it, or run `/compile-lexicon` (see below) against your library.

**4. If your site uses Jekyll** (any `you.github.io` user site does), open
`.github/workflows/scan.yml` and change `data: data` to `data: .paper-feeder` —
a dot-dir Jekyll won't publish. (Plain static site? Leave it as `data`.)

**5. Commit and push:**

```sh
git add config .github .claude seeds && git commit -m "Add paper-feeder" && git push
```

**6. Enable GitHub Pages** — repo **Settings → Pages**, source = your default
branch (user `you.github.io` sites are already on). 

**7. Run it once** — **Actions → `scan` → "Run workflow"**. It fetches, scores,
and commits `feed/index.html` + `feed/feed.xml`. After that it runs daily.

**8. Read it** — your digest is at **`https://you.github.io/feed/`**; subscribe
Feedly to **`https://you.github.io/feed/feed.xml`**. (Optionally add a link to
`/feed/` in your site nav.)

That's it — steps 2–4 are the only edits, and step 7 onward is automatic.
See [`examples/consumer/README.md`](examples/consumer/README.md) for the same in
brief.

## Install / run

**As a GitHub Action** (one step in your workflow):

```yaml
- uses: actions/checkout@v4
- uses: alex-robinson/paper-feeder@v0.1.0
  with: { config: config, data: data, docs: feed }
```

**As a package** (CLI or import):

```sh
pip install "git+https://github.com/alex-robinson/paper-feeder@v0.1.0"
paper-feeder --config config --data data --docs feed
```

Both read `config/{sources,scoring}.yaml`, keep state in `--data`, and write
`index.html` + `feed.xml` to `--docs`.

## Pipeline

```
fetch (RSS + OpenAlex + Crossref)
  → normalize (canonical DOI, reconstruct OpenAlex abstracts)
  → dedupe (by DOI, else normalized-title hash)
  → filter already-seen (data/seen.json)
  → score (weighted keyword lexicon, title-boosted; exclusions veto)
  → render (index.html rolling window + feed.xml)
```

## Reading model: seen vs. unread

- **Emitted** — the scanner has surfaced a paper before. Tracked by `seen.json`
  (keyed by DOI), so each paper is announced exactly once, never duplicated.
- **Read** — you actually read it. The scanner can't know this; your reader does.

**RSS / Feedly is the read/unread queue.** Each paper enters the feed once with
its DOI as a stable `guid`, stays unread until you read it, and reopens fine.

**The HTML page is a rolling `window_days` (default 7) window** — matched papers
persist, relevance-ranked, with a "new" badge on today's, then age out (they
remain in Feedly). RSS stays strictly once-per-paper so Feedly isn't re-spammed.

## Refining the lexicon

`config/scoring.yaml` is the quality lever. Each `include` entry is a literal
phrase (`{term: ..., weight: N}`) or raw regex (`{pattern: ..., weight: N}`);
`exclude` entries veto known false positives. A term in the **title** counts
`title_boost`× its weight; in the abstract, ×1.

The easiest way to refine it is the bundled **`/compile-lexicon` Claude Code
command** (in the consumer template). Drop your BibTeX at `seeds/library.bib` and
run, inside Claude Code:

```
/compile-lexicon seeds/library.bib notes.txt https://your-group.edu/research
```

It reads those sources, proposes weighted additions/exclusions against your
current `scoring.yaml`, and waits for approval before editing. Runs on your
Claude subscription — no API key.

## Optional LLM rerank

Set `llm_rerank.enabled: true` in `scoring.yaml` and implement `maybe_rerank()`
in [`src/paper_feeder/rerank.py`](src/paper_feeder/rerank.py) to rerank the top-N
keyword-scored papers with a model (`pip install "…[llm]"`, needs an API key).
Off and unimplemented by design.

## Develop

```sh
git clone https://github.com/alex-robinson/paper-feeder
cd paper-feeder
pip install -e ".[dev]"
pytest
```

Package layout: `src/paper_feeder/` — `fetch/` (rss/openalex/crossref),
`normalize.py`, `dedupe.py`, `score.py`, `rerank.py`, `seen.py`, `window.py`,
`render.py`, `main.py`. Rendering is stdlib-only; runtime deps are just
`feedparser`, `requests`, `pyyaml`.

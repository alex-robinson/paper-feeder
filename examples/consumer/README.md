# Consumer template

Copy the contents of this directory into the **root of your GitHub Pages repo**
(e.g. `<you>.github.io`) to host your own paper digest:

```
config/sources.yaml               # your journals + OpenAlex/Crossref queries
config/scoring.yaml               # your weighted keyword lexicon
.github/workflows/scan.yml        # runs paper-feeder daily, commits feed/
.claude/commands/compile-lexicon.md
seeds/                            # drop library.bib here for /compile-lexicon
```

Then:

1. Edit `config/sources.yaml` (feeds, `mailto`, and set `link` to your site URL)
   and `config/scoring.yaml` (your lexicon — or run `/compile-lexicon`).
2. Commit and push. Enable **GitHub Pages** for the repo (Settings → Pages).
3. Run the workflow once (Actions → `scan` → "Run workflow"). It writes `feed/`
   and commits it back.
4. Your digest is at `<site>/feed/` and your RSS feed at `<site>/feed/feed.xml`
   — subscribe to that in Feedly.

The daily job is pure Python (no API key). `/compile-lexicon` is the only step
that uses Claude, and it runs interactively on your subscription.

State (`data/seen.json`, `data/window.json`) is created and committed by the
workflow — you don't need to add those files yourself.

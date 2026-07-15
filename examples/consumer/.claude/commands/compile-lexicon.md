---
description: Refine the keyword lexicon in config/scoring.yaml from a BibTeX library, notes, or a URL
argument-hint: "[bib/text files and/or URLs describing your interests]"
---

You are refining the weighted keyword lexicon that drives paper-feeder's
relevance filter. The daily job is pure keyword matching; this command is the
occasional, interactive step where the lexicon is improved. Work carefully and
**propose before writing** — the current lexicon may be hand-tuned.

## Inputs

Sources provided by the user (may be empty): $ARGUMENTS

- Treat each argument as either a local file path or a URL.
- Read local files directly (BibTeX `.bib`, plain-text notes, markdown). You can
  parse BibTeX yourself — extract titles, abstracts, and keywords.
- For URLs, fetch the page and use its readable text (e.g. a research-group or
  personal page describing interests).
- Also read `seeds/library.bib` if it exists and wasn't already listed.
- Always read the current `config/scoring.yaml` — you are editing it, not
  replacing it from scratch.

If no sources are given and `seeds/library.bib` is absent, ask the user to point
you at a `.bib` file, a notes file, or a URL before proceeding.

## The scoring.yaml schema (respect it exactly)

- `title_boost`, `publish_min_score`, `serendipity_count`: leave unless the user
  asks to change them.
- `include`: each entry is one of
    - `{term: "ice sheet", weight: N}` — literal phrase, matched case-insensitively
      with word boundaries; internal spaces also match hyphens ("ice-sheet").
    - `{pattern: "raw regex", weight: N, label: "human label"}` — use for acronyms
      that need explicit boundaries, e.g. `{pattern: "\\bGIA\\b", weight: 4, label: "GIA"}`.
- `exclude`: literal terms or `{pattern: ...}` entries that VETO a paper (drop it
  entirely). Use these to kill known false positives from polysemy.
- Scoring: a term in the TITLE counts `weight * title_boost`; in the abstract, `weight`.

## What to produce

Analyze the sources and propose changes to `include` and `exclude`:

- **Coverage**: add weighted terms for genuinely recurring themes, methods, model
  names, regions, and datasets in the sources. Prefer specific multi-word phrases
  (higher weight) over broad single words (lower weight). Roughly: core niche
  topics 4–5, supporting topics 2–3, broad context 1–2.
- **Variants**: for each important term, cover spelling (US/UK: paleo/palaeo),
  hyphenation, and acronym+expansion. Bake these in so recall doesn't depend on
  the author's exact wording.
- **Exclusions**: propose exclude terms only for concrete false-positive risks you
  can name (e.g. an acronym that collides with a common word, an adjacent field
  that shares vocabulary). Be conservative — an over-broad exclusion silently
  drops relevant papers.
- **Pruning**: suggest removing or down-weighting existing terms that the sources
  show are off-target, but flag these separately — don't remove silently.

## Process (important)

1. Summarize what you learned from the sources (the recurring themes/vocabulary).
2. Present the proposed changes as a clear, grouped diff against the current
   `scoring.yaml` — additions, weight changes, new exclusions, and any suggested
   removals — each with a one-line rationale.
3. **Wait for the user to confirm or adjust.** Only after they approve, edit
   `config/scoring.yaml` in place, preserving its comments and section structure.
4. Do not touch any other file. Do not run the pipeline.

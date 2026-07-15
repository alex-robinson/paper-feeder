# seeds

Drop your BibTeX library here as `library.bib`. It is **not** used by the daily
job — it is source material for refining the keyword lexicon.

Run `/compile-lexicon` inside Claude Code (optionally passing extra files or a
URL, e.g. `/compile-lexicon seeds/library.bib notes.txt https://your-group.edu`)
to have Claude read these sources and propose an updated `config/scoring.yaml`
for your review.

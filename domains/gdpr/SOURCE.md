# GDPR policy source

## Primary source

- **Instrument:** Regulation (EU) 2016/679 of the European Parliament and of the Council of 27 April 2016 (General Data Protection Regulation)
- **CELEX:** 32016R0679
- **Official publication:** Official Journal of the European Union, OJ L 119, 4 May 2016, pp. 1-88
- **Language:** English
- **Official HTML:** https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
- **Official PDF:** https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32016R0679
- **EUR-Lex record:** https://eur-lex.europa.eu/eli/reg/2016/679/oj
- **Downloaded:** 2026-08-12
- **Pages:** 88
- **PDF SHA-256:** `bd84e63f5b622b739a83389afc3b30d240f792bb88d8eb03a816c9a82b0c2499`
- **HTML SHA-256:** `fd3f4cffd90403bd84d09e5f6ecf91ccbf5ee6bc2b96e8a3fc263f354b4f4642`

The authoritative PDF and structured English HTML are stored in `source/` as
`gdpr-official-en.pdf` and `gdpr-official-en.html`. They contain all 173
recitals and Articles 1-99 of the regulation.

## Runtime text

`policy.md` is generated from the official structured HTML with Pandoc
(`html -> gfm`, no line wrapping), not from the PDF. It is kept beside the
source because PiBench policy packs expose agent-facing policy text through a
`policy.md` file. The official PDF remains the authoritative publication when
wording or layout is disputed.

## Current pack status

This directory currently contains the source and design analysis only. It does
not yet contain `db.json`, `tools.json`, scenarios, or a runnable `__init__.py`.
Those artifacts must follow the approved operational scope rather than assume
that every GDPR provision is an action available to one agent.

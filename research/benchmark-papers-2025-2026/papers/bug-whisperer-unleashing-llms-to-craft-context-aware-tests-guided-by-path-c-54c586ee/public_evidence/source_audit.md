# Bug Whisperer source/access audit

Checked 2026-10-15. The 2026 TOSEM article is [DOI 10.1145/3846194](https://doi.org/10.1145/3846194).

- Official ACM PDF request returned 403; Crossref/ORCID metadata identifies a 2026-09-17 TOSEM journal article. OpenAlex reports closed access and no OA full text. The first author's publication page confirms acceptance but has no PDF/source link; exact-title web search found no author/institutional manuscript.
- The local `paper_fulltext.txt` is only a DROPS/metadata landing page, not the 21-page article; it is explicitly not counted as read.
- A same-title public Zenodo record, DOI `10.5281/zenodo.17093597`, exists from 2025-09-10 and describes a 503-case Defects4J focal-method dataset with scripts/results. This predates the 2026 article and does not match its version-specific cohort/model description; no direct link from the 2026 paper or confirmed version lineage was found. Do not call it the 2026 paper's artifact.
- No direct code/data artifact for the 2026 version was found. The older Zenodo package is not downloaded or executed.
- Full review status is access-blocked, not read: `../../../../audit/reviews/071.json`.

# Retrieval v5

2026-10-27: baseline163b58a committed/pushed first. Copied44files from v2;
COPY_MANIFEST records source hashes. `baseline_engine.py` preserves the copied
engine. All changes below happen in this new folder. Local isolated .venv uses
LibCST1.9.0. New code is project-specific fact extraction, not paper reproduction.
Status: implementation; new scoring not yet run. V2/default unchanged.

Completion supersedes implementation status:118tests pass,32new scoped checks.
Frozen113-task comparison: family88/113, family+firstsite74/113, unchanged vs v2;
all275bindings have exact source spans. Four lower-ranked index bindings excluded.
No Qwen/paid call, no native utility measurement. V2 stays default, v5 opt-in.
No tuning after these outcomes. See evaluation_v5/{FREEZE,RESULTS,VALIDATION}.json.

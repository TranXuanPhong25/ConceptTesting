# v15_mrconcept_py CPU validation

2026-10-14. 15 tests in this copy; 30 combined pass, including the zero-card gate preventing generation/scoring.
20 frozen dev tasks prepared; all base tests pass; 424 tool edges and 70 spec clauses. Source/config/task hashes
match protocol.json. No model call in this copy yet: scheduler waits for successful B3 AND B4 scoring.
Original raw response files were copied only for identical-request cache reuse. Proposal summaries, generated
samples, oracle execution and effectiveness reports were not copied. Python/JSON example teaches format only.

Tests: CoverUp_concept/.venv/bin/python -B -m unittest trickcatcher_linefacts.pipelines.v14_obgraph_py.test_experiment trickcatcher_linefacts.pipelines.v15_mrconcept_py.test_experiment -q

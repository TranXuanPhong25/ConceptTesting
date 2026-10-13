# CHANGELOG v9_callfb (copy of v7)

Change vs v7: round 2 = Qwen writes concrete calls for each missed hint, the tool traces the PUT and returns feedback,
up to 2 retries, strict (only tool-verified inputs kept); plain-hybrid control gets the same calls with
validity-only feedback. Files: run_v4.py, v4_worker.py, v4_callfb.py, v4_feedback.py, run.py, config.json.

- 529367e: folder created and registered.
- 7e79c4d: amendment 1, HTTP 400 on over-long round-2 prompts is caught and counted as a request made.
- Status: DROPPED. Worse than v8-strict (RESULTS 11.36: 3/19 tasks vs v8).

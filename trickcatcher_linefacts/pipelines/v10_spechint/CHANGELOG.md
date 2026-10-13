# CHANGELOG v10_spechint (copy of v7)

Change vs v7: BEHAV spec-behaviour concepts (rank 5): requirements mined from the docstring, checked against the PUT
by a quoted-clause gate, turned into hints with witnesses. Files: behaviour.py, behaviour_prompts.py, behav_facts.py,
offline_behav.py, facts.py, tracer.py, evaluate/gen_*/v4_* and run.py, config.json.

- 5ecf6a1: folder created.
- 8a26891: amendment 1, whitespace-normalised quote check; positional parameter renaming.
- 9cc702b: amendment 1b, fixed renaming bug (loop variable shadowed `name`).
- Status: no gain (RESULTS 11.35). Not adopted.

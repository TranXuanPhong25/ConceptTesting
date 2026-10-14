# Language Agent Tree Search

Reviewed 2026-10-14; research only. No reproduction, simulation or implementation started.

[Primary source](https://arxiv.org/html/2310.04406v3)

Paper uses an externally stored action/reasoning tree, MCTS selection and environment feedback. Its value combines LM judgement with self-consistency; terminal observations update search values. Programming evaluation is synthesis, not this project's bug-test setting. Useful architecture reference; applying it to LineFacts needs explicit states, actions and a reliable evaluator.

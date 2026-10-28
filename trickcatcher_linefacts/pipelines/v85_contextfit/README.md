# V85 context-fit continuation

The original run stopped at task125 on a strategy-correction request requiring
9060 tokens in an8192-token context. This continuation allocates output as
`min(requested_max_tokens, 8192 - prompt_tokens)` for both methods. Messages and
the hybrid algorithm stay unchanged. See [registration](PREREG.md).

Reuses all113 preparations,6 completed pairs and509 successful requests from
the same run, checked by content hash and counted within the3503 cumulative cap.
The frozen parent supplies the unchanged generation/scoring implementation.
Source lives here; output uses the parent's existing sandbox output boundary:
`../v85_retrievalhybrid/out/humaneval/comparison_contextfit_1/STATUS.json`.

This is an amended protocol, not a completed original v85 run. Long requests
receive smaller output caps; the final report must include these adjustments.
No efficacy result exists until all113 pairs and shared oracle scoring finish.

2026-10-28 11:12UTC: detached PID30096 launched; restored6pairs and submitted the
formerly blocked correction with3228 output tokens.31 CPU checks pass. Current
STATUS.json is authoritative; do not launch a duplicate controller.

2026-10-28 12:02UTC: controller exited after connectivity failures at25/113 pairs.
574 responses received; one additional completion attempt timed out with unknown
usage (task78 retrieval round1). All113 preparations and25paired results remain
saved. At13:06UTC user requested continuation, but GET/models returned404, so
no new completions were sent. Resume needs a reachable authorized endpoint and
a fresh output root preserving the failed attempt and cumulative3503cap.

15:04UTC: superseded by the running [restored-endpoint continuation](../v85_transport_resume/README.md),
PID54121, output `comparison_contextfit_2`. This root remains terminal.

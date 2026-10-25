# v61 integrated pathfault implementation

This successor implements the missing semantic contract/compositional construction/lifecycle layers after the finite v60 diagnostic. Old v60 code/results are preserved. Read PREREG_V61.md for scope and budget.

New entry point: `pipeline.py`. It combines semantic_contract writer/admission, compositional predicates, joint_constructor native certification, equal-evidence generator controls, final-input audit and immutable cache/freeze. Pure Python source and spec remain public; references and hidden validity contracts are evaluator-only.

Ten targeted authored engineering tests cover joint string/integer constraints, nested input construction, multi-model scalar search, string-literal equality, stable AST IDs and rejection of invented binding/arbitrary predicates, local-event and changed-final-input verification, full orchestration/resume, stale-source rejection and final malformed input handling. Four external scorer regressions also pass.

Code/protocol review passed and the ngrok pilot is active as of2026-10-25 in `out/pipelines/v61_pathfault_integrated/pilot6_20261025/generation_v2/`. Initialtrial is preserved separately after packaging fixes;15targeted regressions pass. No v61 effectiveness score yet. Copied legacy entry points/results are provenance, not this run's results. The semantic writer proposes unverified requirements; quote/source binding does not prove normative correctness. A site hit is not a local-fault/bug certificate.

An independent external supervisor follows exact process identity and bounded transport attempts, then invokes reviewed scoring after generation freeze. Status is in parent `monitor_v2/status.json`; scoring output will be `analysis/v57_completion/out_integrated_v61_reviewed/`. Runtime endpoint/key remain outside repository and logs.

Search bounds and unsupported syntax are explicit. V61 does not claim full Python, arbitrary heap reasoning, general semantic correctness or positive concept gain.

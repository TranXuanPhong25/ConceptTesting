# v23_concepthyp

2026-10-17: direct source copy from v7 (PARENT.json), not v21_flowtools. Parent remains
unchanged. Ports listed with original hashes in PORTS.json; execution trace cap reduced
to2048. No outputs/caches copied. Historical inherited experiment CLIs disabled.

Adds jsonschema-based small semantic diagnostic with separated spec/code contexts,
concept-guided/direct hypothesis proposals and three downstream presentation controls.
Fixed replay uses existing isolated native/traced workers. Adds frozen source/request/
generation lineage, cumulative online attempts, independent post-freeze fixture scoring,
review packets, CPU checks and separate optional small-model concept-use probe.

Status at source freeze: implementation and clean-context audit fixes complete; CPU checks and
small-model probe reported outside package. User authorized Qwen diagnostic16 after providing
an endpoint; no benchmark expansion. Frozen source is not edited after launch.

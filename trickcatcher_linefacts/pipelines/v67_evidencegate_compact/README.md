# v67 evidence gate compact diagnostic

Interface successor of v65_evidencegate: same full writer packet encoded as
compact JSON to fit case66 in8192tokens with1536output. All hypothesis,
public-example, construction, selection and per-case gate behavior is inherited.
See PREREG_V67.md and CHANGELOG.md; older documents describe their named parents.

Entrypoint: python -m trickcatcher_linefacts.pipelines.v67_evidencegate_compact.pipeline
--online --prepare-only --requests ... --out ... --approval ...

This run is limited to six shared writers plus public-only CPU checks. No
arm generation or oracle/scoring. Ref10 remains deferred.

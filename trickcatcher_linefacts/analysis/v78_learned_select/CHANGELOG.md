# v78 learned selection

- Parent: read-only v47 fixed-menu analysis, using v41/v47 cached execution and official checks; no pipeline or author-source mutation.
- Added: isolated CPU supervised leave-one-task-out ranker, context ablation, smoothed priors, exact tie expectations and input-cost-conditioned random controls.
- Status: COMPLETE, registered NO-GO. Primary context18 vs random18.25, context-removed19, subtype prior20.5. Secondary context21 equals both context-free controls.
- Pre-label guard found 33 PUTs /24 specification groups; prospectively amended to leave-problem-group-out with group-balanced training/bootstrap, then independently re-reviewed.
- Verification: 11 synthetic tests; all historical v47 metrics replayed; 1,743 consumed cache files unchanged; 0 API/new program executions.
- Scope: original saved-data diagnostic, not a CASCADE implementation.

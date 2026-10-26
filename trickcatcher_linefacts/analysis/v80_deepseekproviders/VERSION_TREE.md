# v80 version lineage

```text
v72 Qwen raw/full diagnosis on cases85/124
 └─ v73 GPT-OSS: raw85 correct, raw124 wrong, both full abstain
     └─ v79 DeepSeek/Relace: two first-call429, zero answers
         └─ v80 DeepSeek, same four prompts per explicit provider
             ├─ Reka: raw85 correct, full85 supported/admitted; full124 timeout
             └─ DeepInfra/fp8: raw85 correct(extra JSON key); full85 upstream429
```

Concept kind: spec-linked fault hypothesis/local edit in the full writer arm;
raw arm asks ordinary diagnosis. Both have known-bug premise. No input-selection
or v77 combined-concept experiment. Three responses/8planned slots, incomplete;
no causal concept/provider claim. See RESULTS.md and public_review_results.json.

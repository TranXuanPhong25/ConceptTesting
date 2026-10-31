# Doc2OracLL: Investigating the Impact of Documentation on LLM-Based Test Oracle Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [Doc2OracLL: Investigating the Impact of Documentation on LLM-Based Test Oracle Generation](https://doi.org/10.1145/3729354)

Year/venue: 2025 FSE

Dataset: SF110 training; Defects4J unseen bug detection

Input setting: test prefix + Javadoc; with/without method body

Model: Fine-tuned CodeGen-350M, CodeLlama-7B, CodeGemma-7B; other small models; GPT-3.5 documentation generation

Artifact: Not verified

License: Not verified

Concept hook (research judgment): Documentation as normative source; small models thuận lợi nếu released checkpoint được tìm thấy.

Limitation: Paper/model details verified; public artifact and fine-tuned weights not verified in this scan. Base weights không thay thế fine-tuned weights.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:28:13.709393+07:00

Upgrade from source-not-verified to limited author-model evaluation route: one genuine released CodeLlama adapter verified via later author archive. Good concept/oracle prior work; exact whole-paper reproduction remains incomplete.

One actual CodeLlama tc_mut_doc adapter downloaded16,794,456bytes; safetensors header128tensors checked; SHA256 ee78e9cbe9985e2d84da40895b736fb0277e8e9aff79c7b98ecc2553fa8059c9. Full original60-model/prompt checkpoint suite NOT verified. No model loaded/executed.

Blockers: Original arXiv HTML truncates afterRQ1; retrieved/read entire23page officialPDF instead; Original training/evaluation source and full fine-tuned checkpoint suite not located; same-titleGitHub/HF searches empty; Follow-up archive is a different paper artifact and focuses exception prediction; original Defects4J replay route not verified; Provided follow-up script uses absolute scratch paths and docskip file alongside tc_mut_doc variant: reconcile input ablation before evaluating; Base model revisions not pinned; no full training hyperparameter/seed manifest established for60combinations; No author inference/evaluator run; model package format inspection only

Sources: https://arxiv.org/pdf/2412.09360v2, https://doi.org/10.1145/3729354, https://assert-lab.github.io/publications/, https://arxiv.org/html/2608.00884, https://doi.org/10.6084/m9.figshare.30110098.v1

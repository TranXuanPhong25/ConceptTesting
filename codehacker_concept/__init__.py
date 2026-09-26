"""CodeHacker (arXiv 2602.20213) + AutoCode (arXiv 2510.12803) reimplementation
with a verifiable weakness-concept layer.

Modules
-------
data        CodeHacker-Plus / CodeContests+ loading via HTTP range reads, local cache.
sandbox     C++/testlib compilation and resource-limited execution.
judge       Validator, checker, and the paper's three hack conditions, plus
            AnyPoC-style independent re-execution.
llm         Gemini (Vertex) client wrapper with token accounting and a resume cache.
prompts     CodeHacker Appendix L prompts (verbatim) and AutoCode-derived prompts.
autocode    AutoCode validator/checker selection (40 cases, 3 candidates).
calibration CodeHacker Algorithm 1/2 attack-and-refine loops.
analyst     Code Analyst with dual execution (C++ sandbox + Python).
antihash    Lattice (LLL) and birthday collision search for rolling hashes.
generators  Stress, LLM-targeted, and anti-hash generators (the cascade).
concepts    Structured weakness concepts and their execution-based verification.
kb          Mechanism knowledge base (built outside the evaluation set) + retrieval.
pipeline    Per-pair cascade for the baseline and concept conditions.
metrics     HSR, TNR/TPR, VPR, paired statistics.
"""

__all__ = []

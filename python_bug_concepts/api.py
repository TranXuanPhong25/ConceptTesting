"""Public search entry point; use the evaluated v2 retriever for Python code."""
from __future__ import annotations

from pathlib import Path

from .base import DEFAULT_DB, ROOT, get_concept as original_get, search as original_search


def search(query: str = "", *, code: str | None = None, top_k: int = 5,
           category: str | None = None, field: str = "all", source: str | None = None,
           retriever: str = "auto", db: Path | None = None, root: Path = ROOT,
           policy: str | None = None) -> dict:
    """Auto uses v2 for code/all-fields; original lexical search stays available.

    Explicit v2 also supports text queries against its extended corpus. The old
    per-field search and custom-root API continue to use the original engine.
    """
    if retriever not in {"auto", "original", "v2", "v5", "v6"}:
        raise ValueError("retriever must be auto, original, v2, v5 or v6")
    if policy is not None and retriever != "v6":
        raise ValueError("policy is available only with retriever='v6'")
    if retriever == "v6":
        if field != "all" or root != ROOT:
            raise ValueError("v6 uses all fields and its pinned combined corpus; use original for field/custom-root search")
        try:
            from .retrieval_v6.engine import DEFAULT_DB as V6_DB, search as semantic_search
        except ModuleNotFoundError as exc:
            if exc.name == "libcst":
                raise ValueError("v6 requires LibCST; install python_bug_concepts/retrieval_v6/requirements.txt or use its .venv Python") from None
            raise
        return semantic_search(query, code=code, top_k=top_k, category=category,
                               source=source, db=db or V6_DB, policy=policy or "balanced")
    if retriever == "v5":
        if field != "all" or root != ROOT:
            raise ValueError("v5 uses all fields and its pinned combined corpus; use original for field/custom-root search")
        try:
            from .retrieval_v5.engine import DEFAULT_DB as V5_DB, search as scoped_search
        except ModuleNotFoundError as exc:
            if exc.name == "libcst":
                raise ValueError("v5 requires LibCST; install python_bug_concepts/retrieval_v5/requirements.txt or use its .venv Python") from None
            raise
        return scoped_search(query, code=code, top_k=top_k, category=category, source=source, db=db or V5_DB)
    use_v2 = retriever == "v2" or retriever == "auto" and code is not None and field == "all" and root == ROOT
    if use_v2:
        if field != "all" or root != ROOT:
            raise ValueError("v2 uses all fields and its pinned combined corpus; use original for field/custom-root search")
        from .retrieval_v2.engine import DEFAULT_DB, search as improved_search
        return improved_search(query, code=code, top_k=top_k, category=category, source=source, db=db or DEFAULT_DB)
    kwargs = {"code": code, "top_k": top_k, "category": category, "field": field, "source": source, "root": root}
    if db is not None:
        kwargs["db"] = db
    return original_search(query, **kwargs)


def get_concept(concept_id: str, db: Path | None = None) -> dict:
    """Look up original or extended cards without changing the old base API."""
    try:
        return original_get(concept_id, db or DEFAULT_DB)
    except ValueError as exc:
        if not str(exc).startswith("Unknown concept:"):
            raise
    from .retrieval_v2.corpus import cards
    for card in cards():
        if card["id"] == concept_id:
            return card
    raise ValueError("Unknown concept: " + concept_id)

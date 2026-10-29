"""Independent full-corpus candidate recall with shared conservative source binding."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import numpy as np

from . import corpus
from . import engine as parent
from .concept_evidence import feature_views, load_overlay, family_for
from .operation_binding import verdict, VERSION as BINDER_VERSION

VERSION = "operation-hybrid-vr11.1"
VIEWS = ("contract", "mechanism", "trigger")
CHANNELS = {"A": ("structural", "bm25"), "B": ("structural", "bm25", "dense"),
            "C": ("structural", "bm25"), "D": ("structural", "bm25", "dense")}
BUDGET = 12
RRF_K = 60
MAX_SITES = 64


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def tokens(text):
    # Public source names split at snake/camel boundaries; no generated bug summaries.
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return re.findall(r"[^\W_]+", text.lower(), re.UNICODE)


class Lexical:
    """SQLite FTS5 BM25 over every supplied document, without structural eligibility."""
    def __init__(self, documents):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE VIRTUAL TABLE docs USING fts5(id UNINDEXED,body)")
        self.db.executemany("INSERT INTO docs VALUES (?,?)", [(k, " ".join(tokens(v))) for k, v in documents.items()])

    def ranking(self, query):
        terms = list(dict.fromkeys(tokens(query)))[:128]
        if not terms:
            return []
        match = " OR ".join('"' + t + '"' for t in terms)
        return [(k, -float(s)) for k, s in self.db.execute(
            "SELECT id,bm25(docs) AS score FROM docs WHERE docs MATCH ? ORDER BY score,id", (match,))]

    def close(self):
        self.db.close()


def fuse(rankings):
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            key = item[0] if isinstance(item, tuple) else item
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda p: (-p[1], p[0]))


def source_sites(a, evidence, *, spread=False):
    """Shared source-ordered site universe; no channel gets structural-site priority."""
    by_key = {}
    nodes = {a.id(n): n for n in a.nodes if hasattr(n, "lineno") and hasattr(n, "end_lineno")}
    # Ordering independent of retrieval arm/card embeddings.
    for records in evidence.values():
        for row in records:
            n = nodes.get(row.get("fact_id")) or parent._match_node(a, row)
            if n is not None:
                by_key[a.id(n)] = n
    for n in sorted(a.nodes, key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0), type(n).__name__)):
        if isinstance(n, (ast.Call, ast.Subscript, ast.Compare, ast.Assign, ast.AnnAssign,
                          ast.AugAssign, ast.Return, ast.BinOp, ast.IfExp, ast.For, ast.While,
                          ast.If, ast.FunctionDef, ast.AsyncFunctionDef)) and hasattr(n, "end_lineno"):
            by_key.setdefault(a.id(n), n)
    output = []
    ordered = sorted(by_key.items(), key=lambda p: (p[1].lineno, p[1].col_offset, type(p[1]).__name__))
    retained = ([(ordered[(i*(len(ordered)-1))//(MAX_SITES-1)]) for i in range(MAX_SITES)]
                if spread and len(ordered)>MAX_SITES else ordered[:MAX_SITES])
    for fid, n in retained:
        fact = a.fact(n)
        a.records[fid] = fact
        p, child, guards = a.parent.get(n), n, []
        while p is not None and p is not a.owner(n):
            if isinstance(p, (ast.If, ast.While, ast.For)):
                branch = "body" if child in p.body else "else" if child in p.orelse else "header"
                guards.append({"expression": a.text(p.test if hasattr(p, "test") else p.iter)[:240],
                               "control_type": type(p).__name__, "branch": branch,
                               "status": "enclosing_control_not_path_feasibility_proof"})
            child = p
            p = a.parent.get(p)
        value = getattr(n, "value", n)
        if value is None:
            value = n
        origins = a.origins(value)
        effects = [str(x.get("effect", "unknown")) for x in origins]
        text = "\n".join([fact["node_type"], fact["expression"][:600],
                          "Enclosing controls: " + json.dumps(guards), "Local effects: " + " ".join(effects)])
        output.append({"fact": fact, "node": n, "text": text, "guards": guards, "origins": origins})
    return output, len(ordered)


def queries(code, query, a, sites):
    docs = list(dict.fromkeys(a.spec(n) for n in a.nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))))
    spec = "\n".join(d for d in docs if d)
    local = "\n".join(s["text"] for s in sites)
    # These are source views, not model-inferred fault explanations or expected outputs.
    raw = {"contract": query + "\n" + spec, "mechanism": query + "\n" + local,
           "trigger": query + "\nPublic input requirements and examples:\n" + spec}
    caps = {"contract": 2400, "mechanism": 4000, "trigger": 2400}
    return {k: text[:caps[k]] for k, text in raw.items()}, {k: max(0, len(text)-caps[k]) for k, text in raw.items()}


def query_slices(code, query, a, sites, strategy):
    q, omitted = queries(code,query,a,sites)
    result = {view:[text] for view,text in q.items()}
    if strategy=='coverage' and sites:
        # Four interleaved local-operation views cover early and late retained
        # sites. View fusion occurs before channel fusion; extra slices do not
        # create extra candidate channels or a larger candidate budget.
        chunks = ['\n'.join(s['fact']['node_type']+': '+s['fact']['expression'][:88]
                            for s in sites[offset::4]) for offset in range(min(4,len(sites)))]
        result['mechanism'] = [query[:160]+'\n'+chunk[:1600] for chunk in chunks]
        omitted['mechanism']=sum(max(0,len(chunk)-1600) for chunk in chunks)
    return result,omitted


class Retriever:
    def __init__(self, *, encoder=None, binder_policy='operation', query_strategy='legacy', family_diversity=False):
        if binder_policy not in {'legacy','operation'} or query_strategy not in {'legacy','coverage'}:
            raise ValueError('Invalid frozen binder/query policy')
        self.binder_policy=binder_policy
        self.query_strategy=query_strategy
        self.family_diversity=family_diversity
        self.cards = {c["id"]: c for c in corpus.cards()}
        self.overlay = load_overlay()
        self.encoder = encoder
        self._views, self._lexical, self._dense = {}, {}, {}
        for revised in (False, True):
            view = {cid: feature_views(c, revised=revised, overlay=self.overlay) for cid, c in self.cards.items()}
            self._views[revised] = view
            self._lexical[revised] = {v: Lexical({cid: d[v] for cid, d in view.items()}) for v in VIEWS}

    def close(self):
        for indexes in self._lexical.values():
            for idx in indexes.values():
                idx.close()

    def _dense_rank(self, revised, view, text):
        if self.encoder is None:
            raise ValueError("Dense arm requires a pinned local Encoder; no fallback")
        key = (revised, view)
        ids = sorted(self.cards)
        if key not in self._dense:
            self._dense[key] = self.encoder.encode([self._views[revised][cid][view] for cid in ids])
        vector = self.encoder.encode([text])[0]
        scores = self._dense[key] @ vector
        return sorted(zip(ids, map(float, scores)), key=lambda p: (-p[1], p[0]))

    def search(self, query="", *, code, arm="A", top_k=3, category=None, source=None):
        if arm not in CHANNELS or not 1 <= top_k <= 3:
            raise ValueError("arm must be A/B/C/D; top_k must be1..3")
        revised = arm in ("C", "D")
        evidence, spec, symbols, warning, a, excluded = parent._candidates(code)
        if a is None:
            raise ValueError("V7 scoped source unavailable: " + str(warning))
        allowed = {cid for cid, c in self.cards.items() if (category is None or c["category"] == category)
                   and (source is None or any(s["source"] == source for s in c["sources"]))}
        sites, total_sites = source_sites(a, evidence, spread=self.query_strategy=='coverage')
        q, omitted_chars = query_slices(code, query, a, sites, self.query_strategy)
        structural = sorted(((cid, max(1000*r.get("semantic_support", {}).get("tier", 0) + min(r["priority"], 300)
                                      for r in records)) for cid, records in evidence.items() if cid in allowed),
                            key=lambda p: (-p[1], p[0]))
        def filtered(ranking):
            return [x for x in ranking if x[0] in allowed]
        branches = {"structural": structural,
                    "bm25": fuse([fuse([filtered(self._lexical[revised][v].ranking(text)) for text in q[v]]) for v in VIEWS])}
        if "dense" in CHANNELS[arm]:
            branches["dense"] = fuse([fuse([filtered(self._dense_rank(revised, v, text)) for text in q[v]]) for v in VIEWS])
        ranked = fuse(list(branches.values()))[:BUDGET]
        positions = {name: {cid: i+1 for i, (cid, _) in enumerate(rows)} for name, rows in branches.items()}
        candidates, selected, rejected, screened = [], [], [], []
        site_index = Lexical({s["fact"]["id"]: s["text"] for s in sites})
        excluded_keys = {(x["concept_id"], x.get("fact_id")) for x in excluded}
        try:
            for cid, score in ranked:
                card = self.cards[cid]
                origin = {name: ranks[cid] for name, ranks in positions.items() if cid in ranks}
                lexical_sites = dict(site_index.ranking(self._views[revised][cid]["mechanism"]))
                # Recognized relation support comes ONLY from existing evidence records.
                eligible = [s for s in sites if s["fact"]["node_type"] in card["where"]["ast_nodes"]]
                existing = evidence.get(cid, [])
                recognized = {r.get("fact_id"): r for r in existing if r.get("fact_id")}
                options = []
                for s in sites:
                    fid = s["fact"]["id"]
                    if (cid, fid) in excluded_keys:
                        continue
                    old = recognized.get(fid)
                    if old is None and s not in eligible:
                        continue
                    grounding = verdict(a,cid,s['node'],existing=old) if self.binder_policy=='operation' else None
                    if grounding is not None and (grounding['status'].startswith('unbound_') or grounding['status'].startswith('excluded_')):
                        screened.append({'concept_id':cid,'fact_id':fid,'line':s['fact']['span']['line'],**grounding})
                        continue
                    support = old.get("semantic_support", {}) if old else {}
                    tier = support.get("tier", 0)
                    options.append((tier, old.get("priority", 0) if old else 0,
                                    lexical_sites.get(fid, 0), s, old, grounding))
                options.sort(key=lambda o: (-o[0], -o[1], -o[2], o[3]["fact"]["span"]["line"], o[3]["fact"]["span"]["column"]))
                cand = {"concept_id": cid, "score": score, "branch_ranks": origin,
                        "recognized_candidate": bool(existing),
                        "dense_outside_structural": "dense" in origin and cid not in positions["structural"],
                        "dense_top12": origin.get("dense", BUDGET+1) <= BUDGET,
                        "family": family_for(card, overlay=self.overlay)}
                candidates.append(cand)
                if not options:
                    rejected.append({**cand, "reason": "no_eligible_operation_grounded_site" if self.binder_policy=='operation' else "no_matching_ast_type_in_retained_sites",
                                     "possible_site_budget_loss": total_sites > len(sites), "status": "unknown"})
                    continue
                _, _, _, s, old, grounding = options[0]
                f = s["fact"]
                support = old.get("semantic_support", {}) if old else {"tier": 0, "reasons": ["similarity nomination only"]}
                bound = dict(old) if old else {"line": f["span"]["line"], "end_line": f["span"]["end_line"],
                        "expression": f["expression"], "span": f["span"], "fact_id": f["id"], "scope_id": f["scope_id"],
                        "priority": 0, "semantic_support": support, "reason": "Lexical source binding; causal relation unverified",
                        "applicability": {"status": "unknown", "support": [], "contradictions": []}}
                required = self.overlay.get(cid, {}).get("requirements", []) if revised else [
                    {"id": f"original-precondition-{i}", "role": "unclassified", "text": text}
                    for i, text in enumerate(card["where"]["preconditions"])
                ]
                obligations = [{**r, "status": "unknown", "source_evidence": []} for r in required]
                binding = parent._binding(card, bound, a)
                binding.update({"contract_quotes": [{"text": a.spec(s["node"]), "status": "public_text_unaligned"}],
                                "required_conditions": obligations, "local_guards": s["guards"],
                                "recognition": "existing_v6_relation" if old else "similarity_only_unknown",
                                "operation_grounding": grounding})
                selected.append({"concept": card, "score": score, "ranking": cand,
                                 "status": grounding['status'] if grounding else "unverified_fault_hypothesis" if old else "unverified_test_opportunity",
                                 "evidence": [bound], "instantiated": binding,
                                 "mechanism_support": support, "concept_evidence": self.overlay.get(cid) if revised else None})
        finally:
            site_index.close()
        pre_diversity_bound_count=len(selected)
        if self.family_diversity:
            seen_families=set()
            diverse=[]
            for hit in selected:
                family=family_for(hit['concept'],overlay=self.overlay)
                if family not in seen_families:
                    diverse.append(hit)
                    seen_families.add(family)
            selected=diverse
        hits=selected[:top_k]
        return {"engine_version": VERSION, "arm": arm, "query": query, "warning": warning,
                "results": hits, "candidates": candidates, "unbound_candidates": rejected,
                "source_supported_hypotheses": [h for h in hits if h['status']=='source_supported_conditional_hypothesis'],
                "test_opportunities": [h for h in hits if h['status']=='grounded_test_opportunity_contract_unknown'],
                "screened_bindings": screened, "binder_version": BINDER_VERSION,
                "binder_policy":self.binder_policy, "query_strategy":self.query_strategy,
                "family_diversity":self.family_diversity,
                "query_slices_per_view":{v:len(texts) for v,texts in q.items()},
                "query_slice_characters":{v:[len(text) for text in texts] for v,texts in q.items()},
                "pre_diversity_bound_count":pre_diversity_bound_count,
                "bound_candidate_count": len(selected), "excluded_bindings": excluded,
                "candidate_budget": BUDGET, "source_site_count": len(sites), "source_site_cap": MAX_SITES,
                "source_sites_total": total_sites, "source_sites_omitted": total_sites-len(sites),
                "binding_eligibility": "card AST node types or existing recognized pair; missing type is unbound, not safe",
                "query_char_caps": {"contract": 2400, "mechanism": 4000, "trigger": 2400},
                "query_characters_omitted": omitted_chars,
                "branch_top12": {k: [cid for cid, _ in rows[:BUDGET]] for k, rows in branches.items()},
                "representation_sha256": digest(self._views[revised]), "query_view_sha256": digest(q),
                "corpus_sha256": corpus.digest(), "source_sha256": a.sha,
                "model_identity": getattr(self.encoder, "identity", None),
                "limits": ["Similarity and source binding do not establish target bug truth.",
                           "All new obligations remain unknown until evidence-aligned; no oracle is invented.",
                           "Same lexical binder across arms; dense changes recall only."]}


def test_packet(hit, *, factual=False):
    """Explicit downstream packet export; does not modify or run the frozen v85 adapter."""
    packet = {"source_site": hit["instantiated"]["where"], "mechanism": hit["instantiated"]["how"],
              "observable_hypothesis": hit["instantiated"]["what"],
              "public_contract": hit["instantiated"]["contract_quotes"],
              "required_conditions": hit["instantiated"]["required_conditions"],
              "guards": hit["instantiated"]["local_guards"], "status": hit["status"]}
    if not factual:
        packet["concept_id"] = hit["concept"]["id"]
    return packet

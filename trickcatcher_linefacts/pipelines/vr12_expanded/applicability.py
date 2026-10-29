"""Separate bounded hypothesis refutation from observed predicate coverage."""
import ast
import random
from . import fair_generation


def assess(source,entry,binding):
    unknown=dict(status='unknown',reason='no_static_refutation')
    if binding.get('status')!='supported' or binding.get('family')!='membership':return unknown
    tree=ast.parse(source)
    fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==entry),None)
    if fn is None:return unknown
    node=next((n for n in ast.walk(fn) if isinstance(n,ast.Compare) and
               [n.lineno,n.col_offset,n.end_lineno,n.end_col_offset]==binding['site']),None)
    if node is None or len(node.comparators)!=1:return unknown
    table=node.comparators[0]
    evidence=dict(site=binding['site'])
    if isinstance(table,ast.Name):
        name=table.id
        # shortcut: lexical local constants only; use dataflow analysis for wider binding forms.
        if any(isinstance(n,(ast.Global,ast.Nonlocal,ast.Import,ast.ImportFrom,ast.Match,ast.ExceptHandler,ast.Lambda))
               or isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n is not fn
               or isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('exec','eval','locals','globals','vars')
               or isinstance(n,ast.arg) and n.arg==name for n in ast.walk(fn)):return unknown
        writes=[n for n in ast.walk(fn) if isinstance(n,ast.Name) and n.id==name and isinstance(n.ctx,(ast.Store,ast.Del))]
        definitions=[n for n in fn.body if isinstance(n,ast.Assign) and len(n.targets)==1
                     and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name and n.lineno<node.lineno]
        if len(writes)!=1 or len(definitions)!=1:return unknown
        definition=definitions[0];table=definition.value
        evidence.update(local=name,definition_line=definition.lineno)
    if not isinstance(table,ast.Constant) or type(table.value) is not str:return unknown
    if set(table.value)!=set(binding['expected_members']):return unknown
    evidence.update(literal=table.value,hypothesis_members=binding['expected_members'])
    return dict(status='refuted_for_supported_values',reason='literal_class_equals_hypothesis',
                scope='single-character string membership under lexical Python bindings; not whole-function correctness',evidence=evidence)


def pick_valid(records,round1,entry,previous,seed,targeted):
    eligible=fair_generation.unseen_inputs([r for r in records if r['valid']],round1,entry)
    seen={r['call'] for r in previous};eligible=[r for r in eligible if r['call'] not in seen]
    rng=random.Random(seed);selected=[]
    hits=[r for r in eligible if targeted and r['shown_hits'][0]]
    if hits:selected=rng.sample(hits,1)
    # Reserve exploration capacity for a non-hit, including unknown observations.
    rest=[r for r in eligible if r not in selected]
    nonhits=[r for r in rest if targeted and not r['shown_hits'][0]]
    if nonhits:selected+=rng.sample(nonhits,1)
    rest=[r for r in rest if r not in selected]
    return selected+rng.sample(rest,min(2-len(selected),len(rest)))

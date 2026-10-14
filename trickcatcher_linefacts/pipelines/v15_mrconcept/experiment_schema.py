"""LineFacts experiment schemas. Parse model code without executing it in this process."""
import ast
import copy
import json
from . import hypotheses, preconditions, relations

GRAPH_FAMILIES = ('STRICT_BOUNDARY', 'ORDER_TIE', 'MULTIPLICITY', 'SIGN_MAGNITUDE',
                  'STRING_NORMALIZATION', 'EMPTY_SINGLETON', 'STATE_UPDATE', 'RETURN_FLOW')
MR_FAMILIES = ('PERMUTATION', 'MONOTONICITY', 'MULTIPLICITY', 'IDEMPOTENCE', 'ROUND_TRIP')


def pure(source, name, names):
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError('one pure function required')
    fn = tree.body[0]
    if fn.name != name:
        raise ValueError('expected function ' + name)
    params = ast.parse('def f(' + ', '.join(names) + '): pass').body[0].args
    return preconditions.predicate(fn, name, params)


def concepts(node):
    # Inspect this statement's expressions, excluding nested statement bodies.
    exprs = [v for _, v in ast.iter_fields(node) if isinstance(v, ast.expr)]
    exprs += [n for _, v in ast.iter_fields(node) if isinstance(v, list) for n in v if isinstance(n, ast.expr)]
    nodes = [n for expr in exprs for n in ast.walk(expr)]
    tags = {type(node).__name__.upper()}
    for n in nodes:
        if isinstance(n, ast.Compare): tags.add('COMPARE')
        if isinstance(n, ast.Subscript): tags.add('INDEX')
        if isinstance(n, ast.BinOp): tags.add('ARITHMETIC')
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name) and n.func.id in ('sorted', 'reversed', 'min', 'max'):
                tags.add('ORDER')
            if isinstance(n.func, ast.Name) and n.func.id in ('sum', 'len', 'all', 'any'):
                tags.add('AGGREGATE')
            if isinstance(n.func, ast.Attribute) and n.func.attr in ('lower', 'upper', 'strip', 'replace'):
                tags.add('NORMALIZE')
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            tags.add('FILTER_MAP')
    return sorted(tags)


def graph(task, candidates):
    tree = ast.parse(task['put']); source = task['put'].splitlines()
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == task['entry'])
    nodes, edges, labels = {}, {}, {}
    def add_node(line):
        key = 'L' + str(line)
        nodes.setdefault(key, dict(id=key, line=line, code=source[line-1].strip(),
                                  covered=any(r['line']==line and r['covered'] for r in candidates['sites'])))
        return key
    edge_rows = []
    for row in candidates['sites']:
        target = add_node(row['line'])
        for d in row['data']:
            owners = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.lineno <= row['line'] <= n.end_lineno]
            scope = min(owners, key=lambda n:n.end_lineno-n.lineno).lineno if owners else fn.lineno
            edge_rows.append(dict(type='DATA', source=add_node(d['definition']), target=target,
                                  name=d['name'], kind=d['kind'], scope=scope,
                                  evidence='observed base/witness def-use'))
        for c in row['control']:
            edge_rows.append(dict(type='CONTROL', source=add_node(c['line']), target=target,
                                  condition=c['condition'], outcome=c['outcome'],
                                  evidence='AST enclosing guard; approximate control dependence'))
    unique = {json.dumps(e, sort_keys=True):e for e in edge_rows}
    for i, key in enumerate(sorted(unique)):
        edges['E'+str(i)] = dict(id='E'+str(i), **unique[key])
    for key, node in sorted(nodes.items()):
        statements = [n for n in ast.walk(tree) if isinstance(n, ast.stmt) and n.lineno == node['line']]
        syntax_tags = set()
        for stmt in statements: syntax_tags.update(concepts(stmt))
        if node['line']==fn.lineno: syntax_tags.add('INPUT')
        for fact in task['concept_meta']:
            if fact.get('line', fn.lineno)==node['line']: syntax_tags.add('LINEFACT_'+fact['kind'])
        for tag in sorted(syntax_tags):
            cid = 'C'+str(node['line'])+'_'+tag
            labels[cid] = dict(id=cid, label=tag, site=key, evidence='AST syntax / frozen linefact label')
    clauses = {f'R{i+1}':text for i,text in enumerate(relations.clauses(fn))}
    return dict(version='obligation-graph-v1', nodes=nodes, edges=edges, concepts=labels, clauses=clauses,
                base_ok=candidates['base_ok'], trace_statuses=candidates['base_trace_statuses'])


def validate_path(g, ids, concept_ids):
    if not isinstance(ids, list) or not 1 <= len(ids) <= 6 or any(i not in g['edges'] for i in ids):
        raise ValueError('path must contain 1..6 existing typed edge IDs')
    if len(set(ids)) != len(ids): raise ValueError('repeated edge')
    path = [g['edges'][i] for i in ids]
    if any(a['target'] != b['source'] for a,b in zip(path,path[1:])):
        raise ValueError('disconnected path')
    sites = {path[0]['source']} | {e['target'] for e in path}
    if not any(c['site']==path[-1]['target'] and c['label']=='RETURN' for c in g['concepts'].values()):
        raise ValueError('path must terminate at an observable return statement')
    if (not isinstance(concept_ids,list) or not concept_ids or
        any(i not in g['concepts'] or g['concepts'][i]['site'] not in sites for i in concept_ids)):
        raise ValueError('concept must annotate a path node')
    return path


def parse(raw, task, g, method, cap=6):
    values = hypotheses._rows(raw)
    if isinstance(values, dict): values = values.get('cards')
    if not isinstance(values, list): return [], [dict(reason='proposal_parse_failed')]
    kept, failures, seen = [], [], set()
    for i,row in enumerate(values):
        try:
            if i>=cap or not isinstance(row,dict): raise ValueError('proposal cap/schema')
            clause_id = row.get('clause_id')
            if clause_id not in g['clauses']: raise ValueError('unknown exact clause ID')
            family = row.get('family')
            if family not in (GRAPH_FAMILIES if method=='obgraph' else MR_FAMILIES):
                raise ValueError('unknown concept family')
            trigger = hypotheses.trigger_source(row.get('T', row.get('D','')), task)
            card = dict(order=i, clause_id=clause_id, R=g['clauses'][clause_id], family=family,
                        trigger_src=trigger, T=row.get('T',row.get('D','')), semantic_status='candidate',
                        semantic_evidence='exact spec clause ID; model interpretation, not proof')
            if method=='obgraph':
                path = validate_path(g,row.get('path'),row.get('concept_ids'))
                alternative = row.get('alternative')
                if not isinstance(alternative,str) or not alternative.strip(): raise ValueError('missing alternative')
                obligation = pure(row.get('O',''),'obligation',('args','result'))
                card.update(path_ids=row['path'], concept_ids=row['concept_ids'], path=path,
                            concepts=[g['concepts'][c] for c in row['concept_ids']],
                            nodes=[g['nodes'][n] for n in sorted({path[0]['source']}|{e['target'] for e in path})],
                            alternative=alternative, O=row['O'], obligation_src=obligation,
                            path_status='tool-validated adjacency; execution pending')
            else:
                parameter=row.get('parameter')
                params=preconditions.specification(task)[2]
                if type(parameter) is not int or not 0<=parameter<len(params.posonlyargs+params.args):
                    raise ValueError('invalid transformation parameter index')
                transform=pure(row.get('tau',''),'transform',('args',))
                relation=pure(row.get('rho',''),'relation',('args','followup_args','result','followup_result'))
                card.update(parameter=parameter,tau=row['tau'],rho=row['rho'],
                            transform_src=transform,relation_src=relation)
            identity = {k:v for k,v in card.items() if k in
                        ('clause_id','family','path_ids','trigger_src','obligation_src','parameter','transform_src','relation_src')}
            key=json.dumps(identity,sort_keys=True)
            if key in seen:raise ValueError('duplicate_card')
            seen.add(key);kept.append(card)
        except (ValueError,TypeError,SyntaxError,KeyError) as exc:
            failures.append(dict(order=i,reason='proposal_rejected',error=str(exc)[:240]))
    return kept,failures


def visible(card, arm):
    if not card: return 'No accepted candidate for this slot. Generate diverse valid edge cases.'
    common = dict(clause_id=card['clause_id'], R=card['R'], T=card['T'], status='candidate')
    if 'path' in card:
        common.update(O=card['O'], alternative=card['alternative'], nodes=card['nodes'])
        if arm=='card-strategy': common['unordered_evidence']=sorted(card['path'],key=lambda e:e['id'])
        else: common['connected_path']=card['path']
        if arm!='graph-noconcept':common.update(family=card['family'],concepts=card['concepts'])
    else:
        common.update(tau=card['tau'],rho=card['rho'],parameter=card['parameter'])
        if arm!='mr-flatfacts': common['concept_family']=card['family']
    return json.dumps(common,ensure_ascii=False)


def proposal_messages(task, g, method):
    system = 'You are a software tester. Propose falsifiable specification obligations. JSON array only.'
    params = [a.arg for a in preconditions.specification(task)[2].posonlyargs+preconditions.specification(task)[2].args]
    instructions = ("Each object: clause_id, family, concept_ids, path (existing directed edge IDs in connected order), "
        "T (def trigger with original function arguments), O (def obligation(args, result) returning bool), "
        "alternative (a specific incorrect behavior to distinguish). Use only pure builtin expressions, no imports, "
        "no calls to the target. At least one concept must annotate your path. The path MUST end at a RETURN node. "
        "O should check a narrow property, not implement the full algorithm. Families: "+str(GRAPH_FAMILIES)
        if method=='obgraph' else
        "Each object: clause_id, family, parameter (zero-based argument index), D (def trigger with original "
        "function arguments), tau (def transform(args) returning a FULL positional argument tuple), rho "
        "(def relation(args, followup_args, result, followup_result) returning bool). Pure builtin expressions "
        "only, no imports, no target calls. Choose only transformations justified by the quoted specification; "
        "state a restrictive D when necessary. Identity transformations are discarded. Families: "+str(MR_FAMILIES))
    evidence = dict(clauses=g['clauses'])
    if method=='obgraph': evidence.update(nodes=g['nodes'],edges=g['edges'],concepts=g['concepts'])
    user = (f'Function argument order: {params}\nPUT:\n{task["put"]}\nBASE TESTS:\n{task["base"]}\n'
            f'TOOL EVIDENCE:\n{json.dumps(evidence,ensure_ascii=False)}\n{instructions}\n'
            'Propose at most six cards. Include covered sites; a base input in a broad class does not exhaust '
            'the obligation. The PUT can be buggy: do not infer intended semantics merely from its outputs. '
            'If no defensible obligation exists, return []. Never include a witness input.')
    return [dict(role='system',content=system),dict(role='user',content=user)]

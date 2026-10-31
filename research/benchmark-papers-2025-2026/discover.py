"""Bibliographic discovery only; does not implement or execute any paper method."""
import concurrent.futures
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'discovery'
RAW.mkdir(parents=True, exist_ok=True)
FILTER = 'from_publication_date:2025-01-01,to_publication_date:2026-10-14'


def fetch(task):
    query, page = task
    path = RAW / f'{query.lower()}-{page}.json'
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(
        {'search': query, 'filter': FILTER, 'per-page': 200, 'page': page})
    if path.exists():
        return query, json.loads(path.read_text())
    req = urllib.request.Request(url, headers={'User-Agent': 'ConceptTester-bibliography/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        data = json.load(response)
    path.write_text(json.dumps({'retrieved': '2026-10-14', 'source_url': url, **data}, ensure_ascii=False))
    return query, data


def abstract(work):
    index = work.get('abstract_inverted_index') or {}
    tokens = {pos: word for word, positions in index.items() for pos in positions}
    return ' '.join(tokens[pos] for pos in sorted(tokens))


def main():
    tasks = [('Defects4J', p) for p in range(1, 6)] + [('BugsInPy', 1), ('SWT-Bench', 1), ('SWT-Bench', 2)]
    works = {}
    counts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for query, data in pool.map(fetch, tasks):
            counts[query] = data.get('meta', {}).get('count')
            for work in data.get('results', []):
                key = work['id']
                if key not in works:
                    works[key] = {**work, 'discovery_queries': []}
                works[key]['discovery_queries'].append(query)
    records = []
    for work in works.values():
        if work.get('type') not in {'article', 'preprint', 'proceedings', 'dissertation', 'report', 'review'}:
            continue
        title = work.get('title') or ''
        text = (title + ' ' + abstract(work)).lower()
        title_low = title.lower()
        score = sum(weight for terms, weight in [
            (('test generation', 'test case generation', 'test-case generation', 'unit test', 'unit-test', 'test oracle', 'assertion generation', 'reproducing test', 'reproduction test'), 12),
            (('fault detection', 'bug detection', 'bug-revealing', 'fault-revealing', 'non-regress', 'regression test', 'mutation testing'), 8),
            (('program repair', 'fault localization', 'fault localisation', 'debugging', 'root cause'), 4),
            (('large language model', 'llm', 'language models'), 4),
            (('github.com', 'replication package', 'artifact', 'open-source', 'open source'), 2),
        ] if any(term in text for term in terms))
        if any(term in title_low for term in ('test generation', 'test case', 'unit test', 'test oracle', 'assertion', 'reproduction', 'reproducing')):
            score += 8
        if any(term in title_low for term in ('survey', 'systematic', 'review')):
            score -= 8
        loc = work.get('primary_location') or {}
        source = loc.get('source') or {}
        records.append({'openalex_id': work['id'], 'title': title, 'year': work.get('publication_year'),
                        'publication_date': work.get('publication_date'), 'type': work.get('type'),
                        'doi': work.get('doi'), 'primary_url': work.get('doi') or loc.get('landing_page_url'),
                        'pdf_url': (work.get('best_oa_location') or {}).get('pdf_url'),
                        'venue': source.get('display_name'), 'abstract': abstract(work),
                        'discovery_queries': sorted(set(work['discovery_queries'])),
                        'discovery_score': score, 'dataset_use_verified': False,
                        'artifact_verified': False, 'model_verified': False,
                        'verification_status': 'metadata_only_not_confirmed_suitable'})
    # Collapse identical normalized titles, retaining all bibliographic records for audit.
    groups = {}
    for row in records:
        key = ''.join(c for c in row['title'].lower() if c.isalnum())
        if key in groups:
            old = groups[key]
            old['discovery_queries'] = sorted(set(old['discovery_queries'] + row['discovery_queries']))
            old.setdefault('duplicate_record_ids', []).append(row['openalex_id'])
        else:
            groups[key] = row
    rows = sorted(groups.values(), key=lambda r: (-r['discovery_score'], r['title']))
    (ROOT / 'all_candidates.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    summary = {'search_counts': counts, 'unique_openalex_records': len(works),
               'paper_like_records': len(records), 'unique_normalized_titles': len(rows),
               'metadata_only': True}
    (ROOT / 'discovery_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()

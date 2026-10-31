"""Export screening evidence; metadata candidates are never called verified papers."""
import csv
import hashlib
import json
from pathlib import Path
import re
from reviewed import reviewed_records

ROOT = Path(__file__).resolve().parent


def norm(title):
    title = re.sub(r'\((?:experience paper|replicability study)\)', '', title, flags=re.I)
    return ''.join(c for c in title.lower() if c.isalnum())


def arxiv_id(url):
    return (re.search(r'\b(\d{4}\.\d{4,5})\b', url or '') or [None])[0]


def family(row):
    title = row['title'].lower()
    if re.search(r'survey|review|mapping study', title):
        return 'survey_or_review'
    if re.search(r'assert|oracle', title):
        return 'oracle_assertion_candidate'
    if re.search(r'reproduc|reproagent|issue2test|assertflip|otter|icore|echo:', title):
        return 'reproduction_candidate'
    if re.search(r'test.?generation|test.?case|unit.?test|test.?suite|testing', title):
        return 'testing_candidate'
    if re.search(r'program repair|patch|repairagent|bug.fix|debug', title):
        return 'repair_debugging_adjacent'
    if re.search(r'fault locali|fault class|root.cause|fault diagnosis|faults from', title):
        return 'fault_analysis_adjacent'
    return 'other_software_adjacent'


def scope_group(row):
    if row.get('verification_status') != 'primary_source_reviewed':
        return 'unverified_candidates'
    if row['reproduction_grade'] == 'X':
        return 'excluded_or_other_benchmark'
    if 'SWT-Bench' in row['datasets']:
        return 'swt_reproduction'
    if row.get('slug') in {'flow-graph-faults', 'generalizable-apr', 'hierarchical-knowledge', 'bigger-not-better', 'd4c', 'unitcon'}:
        return 'repair_fault_analysis_support'
    return 'core_defects4j_bugsinpy'


def main():
    reviewed = reviewed_records()
    candidates = json.loads((ROOT / 'all_candidates.json').read_text())
    software = re.compile(r'\b(?:software|program\w*|code\w*|coding|bugs?|bug\w+|debug\w*|patch\w*|assert\w*|mutants?|mutation|repos?\w*|swe[- ]|llms?|language models?|java|python|test\w*)\b', re.I)
    disallowed = re.compile(r'islam|madrasah|wind turbine|bearing|cancer|gastric|fault diagnosis.*pump|clinical|soccer|photobiomodulation', re.I)
    rows = []
    seen = set()
    for paper in reviewed:
        if paper['slug'] == 'restricted-oracle-package':
            continue  # Artifact registry is documented in SHORTLIST, not counted as a paper.
        key = norm(paper['title'])
        seen.add(key)
        rows.append({'title': paper['title'], 'year': int(paper['year_venue'][:4]),
                     'year_venue': paper['year_venue'], 'type': 'reviewed_paper_or_artifact',
                     'primary_url': paper['primary_url'], 'discovery_queries': [],
                     'discovery_score': 1000, 'verification_status': 'primary_source_reviewed',
                     'review_slug': paper['slug'], **paper})
    for candidate in candidates:
        if candidate['type'] not in {'article', 'preprint', 'proceedings'}:
            continue
        if not software.search(candidate['title']) or disallowed.search(candidate['title']):
            continue
        if not (candidate.get('primary_url') or '').startswith(('https://', 'http://')):
            continue
        key = norm(candidate['title'])
        if key in seen or any(arxiv_id(candidate['primary_url']) and arxiv_id(candidate['primary_url']) == arxiv_id(p['primary_url']) for p in reviewed):
            continue
        # Known alternative title of the same reviewed study.
        if candidate['title'].startswith(('DISTINCT:', 'Flow Graph-Based Classification of Defects4J Faults')):
            continue
        seen.add(key)
        row = {k: v for k, v in candidate.items() if k != 'abstract'}
        row['year_venue'] = str(row['year']) + ' (discovery metadata; venue/year not primary-verified)'
        row['datasets'] = 'Unknown: search hit does not prove experimental use'
        row['models'] = 'Unknown; not checked'
        row['artifact_url'] = ''
        row['license'] = 'Unknown; not checked'
        row['input_setting'] = 'Unknown; not checked'
        row['reproduction_grade'] = 'U'
        row['concept_hook'] = 'Not assessed'
        row['limitation'] = 'Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.'
        rows.append(row)
    assert len(rows) >= 500, len(rows)
    chosen = rows[:500]
    columns = ['rank', 'title', 'year', 'year_venue', 'family', 'scope_group', 'datasets', 'input_setting',
               'models', 'artifact_url', 'license', 'reproduction_grade', 'verification_status',
               'primary_url', 'openalex_id', 'discovery_queries', 'concept_hook', 'limitation', 'notes_path']
    header = ['# 500 bibliographic screening records (2025–2026)', '',
              '**Đây là screening corpus, không phải 500 paper đã chứng minh phù hợp hoặc reproducible.**', '',
              'A/B/C = mức evidence của nhóm đã đối chiếu nguồn; U = metadata only; X = ngoài scope/không đủ điều kiện.',
              'Không có model run hoặc paper reproduction trong lượt này. Xem [REPORT.md](REPORT.md) và [SHORTLIST.md](SHORTLIST.md).', '',
              '| # | Year | Paper | Family | Evidence | Notes |', '|---:|---:|---|---|---|---|']
    for rank, row in enumerate(chosen, 1):
        row['rank'] = rank
        row['family'] = family(row)
        row['scope_group'] = scope_group(row)
        slug = row.get('slug') or (re.sub(r'[^a-z0-9]+', '-', row['title'].lower()).strip('-')[:75] + '-' + hashlib.sha1(row['title'].encode()).hexdigest()[:8])
        folder = ROOT / 'papers' / slug
        folder.mkdir(parents=True, exist_ok=True)
        row['notes_path'] = str((folder / 'NOTES.md').relative_to(ROOT))
        lines = [f"# {row['title']}", '', f"Reviewed: 2026-10-14. Evidence: {row['verification_status']}. Grade: {row['reproduction_grade']}.", '',
                 f"Paper/record: [{row['title']}]({row['primary_url']})", '', f"Year/venue: {row['year_venue']}", '',
                 f"Dataset: {row['datasets']}", '', f"Input setting: {row['input_setting']}", '', f"Model: {row['models']}", '',
                 f"Artifact: {row['artifact_url'] or 'Not verified'}", '', f"License: {row['license']}", '',
                 f"Concept hook (research judgment): {row['concept_hook']}", '', f"Limitation: {row['limitation']}", '',
                 'Local reproduction: **not performed**. No author source modified.', '']
        if row.get('openalex_id'):
            lines.extend([f"Discovery record: {row['openalex_id']}", '', f"Discovery query: {', '.join(row['discovery_queries'])}; keyword hit is not dataset-use verification.", ''])
        (folder / 'NOTES.md').write_text('\n'.join(lines))
        (folder / 'metadata.json').write_text(json.dumps(row, ensure_ascii=False, indent=2))
        title = row['title'].replace('|', '/')
        header.append(f"| {rank} | {row['year']} | [{title}]({row['primary_url']}) | {row['family']} | {row['reproduction_grade']} | [notes]({row['notes_path']}) |")
    with (ROOT / 'screened_500.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in chosen:
            export = {**row, 'discovery_queries': ', '.join(row['discovery_queries'])}
            writer.writerow(export)
    (ROOT / 'screened_500.json').write_text(json.dumps(chosen, ensure_ascii=False, indent=2))
    (ROOT / 'CATALOG_500.md').write_text('\n'.join(header) + '\n')
    short = ['# Primary-source review: selected papers', '',
             '**A/B/C mô tả evidence về artifact/model route, không phải kết quả chạy lại. U records không nằm trong bảng này.**', '',
             'Scope đã được người dùng xác nhận: có SWT-Bench và APR/fault localization, xếp riêng theo độ phù hợp.', '']
    group_names = {
        'core_defects4j_bugsinpy': 'Lõi: Defects4J / BugsInPy test generation và oracle',
        'swt_reproduction': 'Mở rộng: SWT-Bench issue reproduction',
        'repair_fault_analysis_support': 'Hỗ trợ: program repair / fault taxonomy / targeted synthesis',
        'excluded_or_other_benchmark': 'Ngoài scope hoặc không đủ evidence',
    }
    for group, label in group_names.items():
        part = ['# ' + label, '', '| Paper | Year/venue | Dataset | Author model | Artifact | Grade | Main limitation |',
                '|---|---|---|---|---|---|---|']
        for paper in reviewed:
            if scope_group({**paper, 'verification_status': 'primary_source_reviewed'}) != group:
                continue
            artifact = f"[source/record]({paper['artifact_url']})" if paper['artifact_url'] else 'Not verified'
            part.append(f"| [{paper['title']}]({paper['primary_url']}) | {paper['year_venue']} | {paper['datasets']} | {paper['models']} | {artifact} | {paper['reproduction_grade']} | {paper['limitation']} |")
        (ROOT / (group.upper() + '.md')).write_text('\n'.join(part) + '\n')
        short.extend(['## ' + label, '', *part[2:], ''])
    (ROOT / 'SHORTLIST.md').write_text('\n'.join(short) + '\n')
    from collections import Counter
    stats = {'screening_records': len(chosen), 'primary_source_reviewed': len(reviewed),
             'primary_source_reviewed_papers': sum(r['verification_status'] == 'primary_source_reviewed' for r in chosen),
             'reviewed_artifact_only_records_outside_corpus': 1,
             'grades': dict(Counter(row['reproduction_grade'] for row in chosen)),
             'families': dict(Counter(row['family'] for row in chosen)),
             'scope_groups': dict(Counter(row['scope_group'] for row in chosen)),
             'year_counts': dict(Counter(row['year'] for row in chosen)),
             'locally_reproduced': 0, 'all_500_suitable_verified': False}
    (ROOT / 'screening_summary.json').write_text(json.dumps(stats, indent=2))
    # Keep the inspected artifact-only record in its own folder, outside the 500 paper records.
    for paper in reviewed:
        if paper['slug'] == 'restricted-oracle-package':
            folder = ROOT / 'papers' / paper['slug']
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'NOTES.md').write_text(f"# {paper['title']}\n\nArtifact-only record; excluded from the 500 paper count.\n\nSource: {paper['primary_url']}\n\n{paper['limitation']}\n")
            (folder / 'metadata.json').write_text(json.dumps(paper, ensure_ascii=False, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()

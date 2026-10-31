"""Retrieve public papers/artifact evidence. Never executes paper implementations.

Downloaded/extracted text is NOT an agent-read or reproduced-paper verdict.
"""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlparse, urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit'
GUARD = threading.Lock()
UA = {'User-Agent': 'ConceptTester-public-paper-audit/1.0 (academic reproducibility review)'}
ARTIFACT_HOSTS = ('github.com', 'gitlab.com', 'zenodo.org', 'figshare.com', 'huggingface.co', 'anonymous.4open.science')


class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.links, self.skip = [], [], 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag in ('p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'li', 'tr', 'br'):
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)
        if tag in ('p', 'div', 'section', 'li', 'tr'):
            self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
    def text(self):
        return '\n'.join(s.strip() for s in ''.join(self.parts).splitlines() if s.strip())


def write_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(path)


def get_public(url, dest, limit=18_000_000):
    result = {'requested_url': url, 'checked_at': datetime.now(timezone.utc).isoformat()}
    try:
        with requests.get(url, headers=UA, timeout=(8, 22), stream=True) as response:
            result.update(status=response.status_code, final_url=response.url,
                          content_type=response.headers.get('Content-Type', ''))
            if response.status_code != 200:
                return result, None
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > limit:
                    result['error'] = 'size_limit'
                    return result, None
                chunks.append(chunk)
            body = b''.join(chunks)
            result['bytes'] = len(body)
            dest.write_bytes(body)
            return result, body
    except requests.RequestException as exc:
        result['error'] = type(exc).__name__  # No sensitive request/context logging.
        return result, None


def looks_fulltext(text):
    count = len(text.split())
    bad = any(s in text[:1500].lower() for s in ('checking your browser', 'captcha', 'access denied', 'just a moment'))
    signals = sum(bool(re.search(pattern, text, re.I)) for pattern in
                  [r'\babstract\b', r'\bintroduction\b', r'\b(?:evaluation|methodology|experimental|results)\b', r'\breferences\b'])
    return not bad and count >= 1600 and signals >= 3


def metadata_index():
    by_id, by_title = {}, {}
    for path in sorted((ROOT / 'discovery').glob('*.json')):
        for work in json.loads(path.read_text()).get('results', []):
            by_id[work['id']] = work
            key = re.sub(r'\W', '', (work.get('title') or '').lower())
            by_title[key] = work
    return by_id, by_title


def paper_urls(row, indexes):
    by_id, by_title = indexes
    meta = by_id.get(row.get('openalex_id')) or by_title.get(re.sub(r'\W', '', row['title'].lower())) or {}
    urls = [row['primary_url']]
    if row.get('pdf_url'):
        urls.append(row['pdf_url'])
    for loc in meta.get('locations', []):
        urls.extend(u for u in [loc.get('landing_page_url'), loc.get('pdf_url'), loc.get('id')] if u)
    arxivs = list(dict.fromkeys(m.group(1) for u in urls for m in re.finditer(r'(\d{4}\.\d{4,5})', u)))
    priority = [f'https://arxiv.org/html/{i}' for i in arxivs] + [f'https://arxiv.org/pdf/{i}' for i in arxivs]
    urls = priority + urls
    return list(dict.fromkeys(u.replace('http://arxiv.org/', 'https://arxiv.org/') for u in urls if u.startswith(('http://', 'https://'))))


def extract_body(body, result, folder, index):
    if body.startswith(b'%PDF'):
        pdf = folder / f'paper-{index}.pdf'
        pdf.write_bytes(body)
        txt = folder / f'paper-{index}.txt'
        command = subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)], capture_output=True, timeout=40)
        if command.returncode or not txt.exists():
            return '', []
        return txt.read_text(errors='replace'), []
    parser = Extract()
    parser.feed(body.decode('utf-8', errors='replace'))
    return parser.text(), [urljoin(result['final_url'], x) for x in parser.links]


def artifact_candidates(text, links, row):
    candidates = {}
    if row.get('artifact_url'):
        candidates[row['artifact_url']] = 'previous_scan_link_not_revalidated'
    # Paper URL extraction is discovery only: references can point to baseline artifacts.
    all_urls = links + re.findall(r'https?://[^\s<>"\[\]]+', text)
    for url in all_urls:
        url = url.rstrip('.,;):')
        host = urlparse(url).netloc.lower()
        if not any(h in host for h in ARTIFACT_HOSTS):
            continue
        if 'github.com' in host:
            m = re.match(r'https?://github\.com/([^/\s]+)/([^/\s?#]+)', url)
            if not m or any(x in m.group(1).lower() for x in ('latexml', 'issues', 'topics')):
                continue
            url = f'https://github.com/{m.group(1)}/{m.group(2)}'.rstrip('/')
            if url.endswith('.git'):
                url = url[:-4]
        candidates.setdefault(url, 'paper_link_candidate_author_relationship_unverified')
    return [{'url': u, 'provenance': p} for u, p in candidates.items()][:50]


def probe_artifact(url, folder, serial):
    dest = folder / f'artifact-{serial}.html'
    result, body = get_public(url, dest, limit=4_000_000)
    result['author_relationship_verified'] = False
    if not body:
        return result
    text, _ = extract_body(body, result, folder, 100 + serial)
    (folder / f'artifact-{serial}.txt').write_text(text)
    result['text_path'] = str((folder / f'artifact-{serial}.txt').relative_to(ROOT))
    result['restricted_signal'] = bool(re.search(r'(?:files.{0,30}restricted|request access|repository not found|this repository is empty)', text, re.I))
    result['license_signal'] = list(dict.fromkeys(re.findall(r'Apache-2\.0|MIT license|BSD-\d-Clause|GPL-\d\.0|CC-BY-\d\.0', text, re.I)))
    result['readme_available'] = bool(re.search(r'readme|quick start|installation|getting started|replication', text, re.I))
    return result


def collect_one(row, indexes, retry=False):
    folder = ROOT / Path(row['notes_path']).parent / 'public_evidence'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'retrieval.json'
    if output.exists() and not retry:
        return json.loads(output.read_text())
    info = {'rank': row['rank'], 'title': row['title'], 'checked_at': datetime.now(timezone.utc).isoformat(),
            'attempts': [], 'retrieval_status': 'unavailable', 'agent_reviewed': False,
            'locally_reproduced': False, 'public_source_verified': False}
    best, best_links = '', []
    for idx, url in enumerate(paper_urls(row, indexes)[:7]):
        result, body = get_public(url, folder / f'page-{idx}.bin')
        info['attempts'].append(result)
        if not body:
            continue
        try:
            text, links = extract_body(body, result, folder, idx)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            result['extraction_error'] = True
            continue
        if len(text) > len(best):
            best, best_links = text, links
            info['text_source_url'] = result['final_url']
        if looks_fulltext(text):
            info['retrieval_status'] = 'fulltext_available_unread'
            best, best_links = text, links
            info['text_source_url'] = result['final_url']
            break
    if best:
        text_path = folder / 'paper_fulltext.txt'
        text_path.write_text(best)
        info['fulltext_path'] = str(text_path.relative_to(ROOT))
        info['word_count'] = len(best.split())
        info['sha256'] = hashlib.sha256(best.encode()).hexdigest()
        if info['retrieval_status'] == 'unavailable':
            info['retrieval_status'] = 'landing_or_partial_only'
        info['dataset_mentions'] = list(dict.fromkeys(re.findall(r'Defects4J(?:-\w+)?|BugsInPy|SWT[- ]Bench(?:[- ](?:Lite|Verified))?', best, re.I)))
        info['artifact_candidates'] = artifact_candidates(best, best_links, row)
        info['artifact_probes'] = []
        # Validate the prior scan's link; newly discovered links need agent provenance review first.
        if row.get('artifact_url'):
            info['artifact_probes'].append(probe_artifact(row['artifact_url'], folder, 0))
        paragraphs = best.splitlines()
        useful = [p for p in paragraphs if re.search(r'available|replicat|artifact|source code|github|checkpoint|huggingface|defects4j|bugsinpy|swt.bench|gpt-|gemini|deepseek|qwen|llama', p, re.I)]
        (folder / 'discovery_excerpts.txt').write_text('\n'.join(useful))
    write_json(output, info)
    with GUARD:
        with (AUDIT / 'retrieval_progress.jsonl').open('a') as stream:
            stream.write(json.dumps({'rank': row['rank'], 'status': info['retrieval_status'], 'words': info.get('word_count', 0)}, ensure_ascii=False) + '\n')
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=500)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--retry', action='store_true')
    args = parser.parse_args()
    rows = json.loads((ROOT / 'screened_500.json').read_text())
    rows = [r for r in rows if args.start <= r['rank'] <= args.end]
    indexes = metadata_index()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(collect_one, r, indexes, args.retry): r for r in rows}
        for future in concurrent.futures.as_completed(futures):
            row = futures[future]
            try:
                result = future.result()
                print(f"{row['rank']:03d} {result['retrieval_status']} words={result.get('word_count', 0)}", flush=True)
            except Exception as exc:
                print(f"{row['rank']:03d} retrieval_worker_error={type(exc).__name__}", flush=True)


if __name__ == '__main__':
    main()

import heapq
import json
import shutil
import subprocess
import csv
import os
import sys
import re
import time
import argparse
import platform
from pathlib import Path
from typing import Optional, Tuple

# ============================================================================
# Path Configuration
# ============================================================================
ROOT = Path(__file__).resolve().parents[1]       # Repository root
SCRIPT_DIR = Path(__file__).resolve().parent      # evaluation/ directory
CONFIG_FILE = ROOT / "src" / "panta" / "config.ini"
EXECUTE_SCRIPT = ROOT / "execute.py"


def extract_config_data(src_file_obj, project_name, max_complexity, prompt_type, model,
                        preserve_existing_test=False):
    """Build config dict for a given source file and project."""
    if project_name == "Gson-16f":
        project_dir = "defects4j-subjects-notests/" + project_name + "/gson"
    else:
        project_dir = "defects4j-subjects-notests/" + project_name

    src_path = src_file_obj["src_path"].replace("defects4j-subjects", "defects4j-subjects-notests")
    src_path = src_path.lstrip("../")

    file_name = os.path.basename(src_path)
    dir_name = os.path.dirname(src_path)

    if project_name == "JxPath-22f":
        test_dir = dir_name.replace("src/java", "src/test")
    else:
        test_dir = dir_name.replace("src/main/java", "src/test/java")

    test_name = file_name.replace(f"{src_file_obj['src_name']}.java", f"{src_file_obj['src_name']}Test.java")
    test_path = os.path.join(test_dir, test_name).replace('\\', '/')

    if os.path.exists(test_path) and not preserve_existing_test:
        os.remove(test_path)

    test_file_name = os.path.splitext(test_name)[0]
    code_coverage_report_path = project_dir + "/target/jacoco/jacoco.csv"
    test_execution_command = f"mvn clean package -Dtest={test_file_name}"

    return {
        'default': {
            'project_directory': project_dir,
            'source_code_file': src_path,
            'test_code_file': test_path,
            'code_coverage_report_path': code_coverage_report_path,
            'test_execution_command': test_execution_command,
            'test_code_command_dir': project_dir,
            'maximum_iterations': str(max_complexity),
            'no_coverage_increase_iterations': '3',
            'junit_version': '4',
            'prompt_type': prompt_type,
            'model': model,
            'enable_fixing': '3',
            'enable_symbolic_execution': 'false',
            'enable_LLM_path_solving': 'false',
            'enable_LLM_verify': 'false',
            'llm_verify_max_rejections': '3',
            'num_tests_initial': '0',
        }
    }


def fill_config(config_data, config_file=None):
    """Update a config.ini using regex to preserve formatting and comments.

    Args:
        config_file: Path to the config file to update.
                     Defaults to the shared CONFIG_FILE when None.
    """
    target = config_file if config_file else CONFIG_FILE
    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    for key, value in config_data['default'].items():
        pattern = rf'({key}\s*=\s*).*'
        content = re.sub(pattern, lambda m, v=value: m.group(1) + v, content)

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_iterations_from_output(output_lines):
    """Parse how many iterations completed from panta log output.

    Counts every iteration that finished its coverage-check step, whether or not
    coverage improved.  Both log messages come from panta.py's run() method:
      - "Iteration N increased line coverage ..."   (coverage went up)
      - "Iteration N cannot increase coverage."     (coverage stayed the same)
    The early-exit exception path ("iteration stops due to error") does not emit
    one of these messages for the partial iteration, so it is excluded — which is
    correct because that iteration never fully completed.
    """
    iterations = 0
    pattern = re.compile(r'Iteration (\d+) (?:increased|cannot increase)')
    early_exit = False
    for line in output_lines:
        m = pattern.search(line)
        if m:
            iterations = max(iterations, int(m.group(1)) + 1)
        if 'iteration stops due to error' in line:
            early_exit = True
    if early_exit and iterations == 0:
        # An exception fired before the first coverage-check message was emitted.
        # Return -1 so callers can distinguish "crashed immediately" from "ran 0 improving iters".
        return -1
    return iterations


def _decode_html_report(html_path: str) -> Optional[str]:
    """Read an HTML report robustly even when embedded logs contain bad bytes."""
    if not os.path.exists(html_path):
        return None

    with open(html_path, 'rb') as f:
        raw = f.read()

    for encoding, errors in (('utf-8', 'strict'), ('utf-8', 'replace'), ('latin-1', 'strict')):
        try:
            return raw.decode(encoding, errors=errors)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


def _extract_numeric_cell(cell_html: str) -> Optional[float]:
    """Extract a numeric value from a table cell."""
    text = re.sub(r'<[^>]+>', '', cell_html)
    text = text.replace('&nbsp;', ' ').strip()
    if not text:
        return None

    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return None

    try:
        return round(float(match.group(0)), 2)
    except ValueError:
        return None


def read_coverage_from_html(html_path: str) -> Optional[Tuple[float, float]]:
    """
    Parse final line and branch coverage from the last INFO row of the HTML report.

    Returns:
        (line_coverage, branch_coverage) when successfully parsed, otherwise None.
    """
    try:
        content = _decode_html_report(html_path)
        if not content:
            return None

        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', content, re.DOTALL | re.IGNORECASE)
        for row in reversed(rows):
            tds = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
            if len(tds) < 6:
                continue

            first_cell = re.sub(r'<[^>]+>', '', tds[0]).replace('&nbsp;', ' ').strip()
            if first_cell != 'INFO':
                continue

            line_cov = _extract_numeric_cell(tds[4])
            branch_cov = _extract_numeric_cell(tds[5])
            if line_cov is not None and branch_cov is not None:
                return line_cov, branch_cov

    except Exception as e:
        print(f"Warning: could not read coverage from {html_path}: {e}")

    return None


def read_coverage_from_output(output_lines) -> Optional[Tuple[float, float]]:
    """Extract the latest coverage numbers from captured Panta output."""
    patterns = [
        re.compile(r'Current line Coverage:\s*([0-9]+(?:\.[0-9]+)?)%,\s*branch coverage:\s*([0-9]+(?:\.[0-9]+)?)%'),
        re.compile(r'Current Coverage:\s*\(([0-9]+(?:\.[0-9]+)?)%,\s*([0-9]+(?:\.[0-9]+)?)%\)'),
    ]

    latest = None
    for line in output_lines:
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                latest = (round(float(match.group(1)), 2), round(float(match.group(2)), 2))
    return latest


def fill_config_and_execute(src_f, proj_name, iter_num, prompt_type, model,
                            config_file=None, preserve_existing_test=False):
    """Update config and run execute.py. Returns a metrics dict.

    Args:
        config_file: Per-worker config path. Uses shared CONFIG_FILE when None.
    """
    config_data = extract_config_data(
        src_f, proj_name, iter_num, prompt_type, model,
        preserve_existing_test=preserve_existing_test
    )
    fill_config(config_data, config_file=config_file)

    start_time = time.time()

    cmd = [sys.executable, str(EXECUTE_SCRIPT)]
    if config_file:
        cmd += ['--config', str(config_file)]

    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_lines = []
    for line in process.stdout:
        print(line, end='')
        output_lines.append(line)

    exit_code = process.wait()
    execution_time = round(time.time() - start_time, 2)

    iterations = parse_iterations_from_output(output_lines)

    sanitized_model = model.replace('/', '_')
    html_path = (ROOT / "result-files"
                 / f"{prompt_type}_{sanitized_model}"
                 / f"{src_f['src_name']}_{prompt_type}_test_results.html")
    coverage = read_coverage_from_html(str(html_path))
    if coverage is None:
        coverage = read_coverage_from_output(output_lines)
    if coverage is None:
        coverage = (0.0, 0.0)
    line_cov, branch_cov = coverage

    return {
        'iterations': iterations,
        'line_coverage': line_cov,
        'branch_coverage': branch_cov,
        'execution_time': execution_time,
        'exit_code': exit_code,
    }


def get_d4j_subject_classes():
    """Read class list from CSV."""
    d4j_subjects = {}
    class_list_path = SCRIPT_DIR / "data" / "class_list.csv"
    with open(class_list_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            project_name, class_name, max_cc = row[0], row[1], row[2]
            if project_name not in d4j_subjects:
                d4j_subjects[project_name] = {}
            d4j_subjects[project_name][class_name] = max_cc
    return d4j_subjects


def read_config_defaults():
    """Read prompt_type and model from config.ini (supports IDE run button)."""
    if not CONFIG_FILE.exists():
        return None, None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    prompt_match = re.search(r'(?m)^prompt_type\s*=\s*(\S+)', content)
    model_match = re.search(r'(?m)^model\s*=\s*(\S+)', content)
    prompt = prompt_match.group(1) if prompt_match else None
    model = model_match.group(1) if model_match else None
    return prompt, model


def run_for_projects(projects, prompt, model, result_path, csv_file,
                     config_file=None, rerun=False):
    """Sequential processing loop over a list of projects.

    Used by both sequential mode and each parallel worker.

    Args:
        rerun: When True, rerun only classes that already have an HTML result.
    """
    defects4j_subject_classes = get_d4j_subject_classes()

    fieldnames = ['project', 'class', 'max_complexity', 'iterations',
                  'line_coverage', 'branch_coverage', 'execution_time', 'exit_code']

    for p_name in projects:
        codefiles_path = SCRIPT_DIR / "defects4j-codefiles" / f"{p_name}-codefiles.json"
        with open(codefiles_path, 'r') as f:
            data = json.load(f)

        file_objects = (data["src_test_exact_match"]
                        + data["src_test_fuzz_match"]
                        + data["src_without_tests"])
        class_subjects = defects4j_subject_classes.get(p_name, {})

        for src_file in file_objects:
            if src_file["src_name"] not in class_subjects:
                continue

            max_cc = class_subjects[src_file["src_name"]]
            html_file = result_path / f"{src_file['src_name']}_{prompt}_test_results.html"

            has_existing_result = html_file.exists()
            if not rerun and has_existing_result:
                print(f"Skipped: {src_file['src_name']} (already processed)")
                continue
            if rerun and not has_existing_result:
                print(f"Skipped: {src_file['src_name']} (no existing result to rerun)")
                continue

            print(f"\n--- {src_file['src_name']} ({p_name}, max_cc={max_cc}) ---")

            try:
                metrics = fill_config_and_execute(
                    src_file, p_name, max_cc, prompt, model,
                    config_file=config_file,
                    preserve_existing_test=rerun,
                )
            except KeyboardInterrupt:
                print("\nInterrupted.")
                sys.exit(1)

            row = {
                'project': p_name,
                'class': src_file['src_name'],
                'max_complexity': max_cc,
                'iterations': metrics['iterations'],
                'line_coverage': metrics['line_coverage'],
                'branch_coverage': metrics['branch_coverage'],
                'execution_time': metrics['execution_time'],
                'exit_code': metrics['exit_code'],
            }

            file_exists = csv_file.exists()
            with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
                csvfile.flush()

            print(f"Iter={metrics['iterations']}, "
                  f"Line={metrics['line_coverage']}%, "
                  f"Branch={metrics['branch_coverage']}%, "
                  f"Time={metrics['execution_time']}s, "
                  f"Exit={metrics['exit_code']}")

    print("\nDone.")


# ============================================================================
# Project metadata and work distribution
# ============================================================================

# Number of target classes per project (used to balance worker loads)
PROJECT_CLASS_COUNTS = {
    "Math-2f": 30,
    "Lang-4f": 17,
    "JxPath-22f": 12,
    "Time-13f": 11,
    "Compress-47f": 9,
    "JacksonCore-26f": 9,
    "JacksonDatabind-112f": 9,
    "Jsoup-93f": 8,
    "Codec-18f": 7,
    "Collections-28f": 5,
    "Gson-16f": 4,
    "JacksonXml-5f": 4,
    "Csv-16f": 3,
    "Cli-40f": 2,
}


def distribute_projects(projects, num_workers):
    """Assign projects to workers so total class counts are as equal as possible.

    Uses the greedy LPT (Longest Processing Time) heuristic:
    sort projects by class count descending, then repeatedly assign the next
    project to whichever worker currently has the fewest classes.
    """
    sorted_projects = sorted(
        projects,
        key=lambda p: PROJECT_CLASS_COUNTS.get(p, 0),
        reverse=True
    )
    # Min-heap entries: (current_total_classes, worker_id, project_list)
    heap = [(0, i, []) for i in range(num_workers)]
    heapq.heapify(heap)

    for project in sorted_projects:
        total, worker_id, proj_list = heapq.heappop(heap)
        proj_list.append(project)
        heapq.heappush(heap, (total + PROJECT_CLASS_COUNTS.get(project, 0),
                              worker_id, proj_list))

    # Return project lists ordered by worker_id
    result = sorted(heap, key=lambda x: x[1])   # sort by worker_id
    return [proj_list for _, _, proj_list in result]


# ============================================================================
# Entry point
# ============================================================================

ALL_PROJECTS = [
    "Math-2f", "JacksonXml-5f", "Csv-16f", "Collections-28f", "Gson-16f",
    "Cli-40f", "JacksonCore-26f", "JxPath-22f", "Jsoup-93f",
    "Codec-18f", "Compress-47f", "JacksonDatabind-112f", "Time-13f", "Lang-4f",
]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run Panta on Defects4J classes and record metrics')
    parser.add_argument('prompt_type', nargs='?', help='Prompt type (e.g. control)')
    parser.add_argument('model', nargs='?', help='Model name (e.g. openai/gpt-4o-mini)')
    parser.add_argument('--workers', type=int, default=6,
                        help='Number of parallel workers, each in its own window (default: 1)')
    parser.add_argument('--rerun', action='store_true', default=False,
                        help='Rerun already-processed classes instead of skipping them')
    # Internal arguments — set automatically when coordinator spawns a worker
    parser.add_argument('--worker-id', type=int, default=None)
    parser.add_argument('--worker-projects', type=str, default=None)
    args = parser.parse_args()

    # ── Resolve prompt / model ─────────────────────────────────────────────────
    if args.prompt_type and args.model:
        prompt = args.prompt_type
        model = args.model
    else:
        print("No arguments provided, reading from config.ini...")
        prompt, model = read_config_defaults()
        if not prompt or not model:
            print("Error: could not read prompt_type and model from config.ini")
            sys.exit(1)
        print("Read from config.ini successfully")

    sanitized_model = model.replace('/', '_')
    result_path = ROOT / "result-files" / f"{prompt}_{sanitized_model}"

    # ── Worker mode (launched by coordinator) ──────────────────────────────────
    if args.worker_id is not None:
        worker_projects = json.loads(args.worker_projects)
        worker_config = ROOT / "src" / "panta" / f"config_worker_{args.worker_id}.ini"
        worker_csv = SCRIPT_DIR / "data" / f"metrics_{prompt}_{sanitized_model}_worker_{args.worker_id}.csv"

        print(f"\n[Worker {args.worker_id}] Projects : {worker_projects}")
        print(f"[Worker {args.worker_id}] Config   : {worker_config}")
        print(f"[Worker {args.worker_id}] CSV      : {worker_csv}\n")

        run_for_projects(worker_projects, prompt, model, result_path,
                         worker_csv, config_file=worker_config, rerun=args.rerun)
        sys.exit(0)

    # ── Sequential mode (--workers 1, default) ─────────────────────────────────
    if args.workers == 1:
        csv_file = SCRIPT_DIR / "data" / f"metrics_{prompt}_{sanitized_model}.csv"

        print(f"\nPrompt : {prompt}  |  Model: {model}")
        print(f"Results: {result_path}")
        print(f"CSV    : {csv_file}\n")

        run_for_projects(ALL_PROJECTS, prompt, model, result_path, csv_file,
                         rerun=args.rerun)
        sys.exit(0)

    # ── Parallel mode (--workers N > 1) ────────────────────────────────────────
    num_workers = args.workers

    # Distribute projects so each worker handles a similar total number of classes
    worker_project_lists = distribute_projects(ALL_PROJECTS, num_workers)

    print(f"\nPrompt : {prompt}  |  Model: {model}")
    print(f"Results: {result_path}")
    print(f"\nLaunching {num_workers} workers:")
    for i, projects in enumerate(worker_project_lists):
        csv_path = SCRIPT_DIR / "data" / f"metrics_{prompt}_{sanitized_model}_worker_{i}.csv"
        print(f"  Worker {i}: {projects}")
        print(f"           CSV -> {csv_path}")

    # Create a per-worker copy of config.ini so workers never touch the shared one
    for i in range(num_workers):
        worker_config = ROOT / "src" / "panta" / f"config_worker_{i}.ini"
        shutil.copy(CONFIG_FILE, worker_config)

    # Launch each worker in its own console window
    script_path = Path(__file__).resolve()
    is_windows = platform.system() == 'Windows'

    processes = []
    for i in range(num_workers):
        cmd = [
            sys.executable, str(script_path),
            prompt, model,
            '--worker-id', str(i),
            '--worker-projects', json.dumps(worker_project_lists[i]),
        ]
        if args.rerun:
            cmd.append('--rerun')
        popen_kwargs = {'cwd': str(ROOT)}
        if is_windows:
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_CONSOLE

        p = subprocess.Popen(cmd, **popen_kwargs)
        processes.append(p)
        print(f"Launched Worker {i} (PID {p.pid})")

    print(f"\nAll {num_workers} workers running. Waiting for completion...")

    # Wait for all workers; clean up config copies when done
    try:
        for i, p in enumerate(processes):
            p.wait()
            print(f"Worker {i} finished (exit code {p.returncode})")
    finally:
        for i in range(num_workers):
            worker_config = ROOT / "src" / "panta" / f"config_worker_{i}.ini"
            if worker_config.exists():
                worker_config.unlink()

    print(f"\nAll workers completed.")
    print(f"CSVs written to: {SCRIPT_DIR / 'data'}/")

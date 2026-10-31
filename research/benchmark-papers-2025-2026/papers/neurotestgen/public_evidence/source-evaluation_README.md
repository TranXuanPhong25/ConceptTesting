## Defects4J Subjects Evaluation

This directory contains the evaluation assets for the Defects4J study, including the precomputed codefile manifests, the 130 target classes in `data/class_list.csv`, execution scripts, and post-processing utilities.

## Evaluation Structure
```text
evaluation/
|-- data/                            # generated statistics, metrics CSVs, and analysis spreadsheets
|-- defects4j-codefiles/             # per-project source/test manifests and CFG-derived metadata
|-- defects4j-sample/                # sample generated tests discussed in the paper
|-- compute_statistics.py            # recompute codefile manifests and subject-level statistics
|-- count_classes_with_high_complexity.py
|-- execute_classes_with_high_complexity.py
|-- execute_classes_pick_one.py
|-- execute_symprompt.py
|-- extract_pass_rate.py
|-- extract_paths_and_analyze.py
|-- result-html-parser.py
|-- result-parser-different-models.py
|-- setup_d4j-subjects.sh
`-- README.md
```

## Included Artifacts

The repository already includes the main evaluation inputs and outputs used by the scripts:

- `defects4j-codefiles/*.json`: source/test mappings and method-level metadata for each subject
- `data/class_list.csv`: the 130 selected high-complexity target classes
- `data/subject_statistics.csv`: project-level statistics
- `data/metrics_*.csv`: per-run metrics captured during execution
- `data/coverage_statistics*.csv`, `data/pass_rate_statistics.csv`: parsed summary tables
- `data/path_analysis_by_class.csv`, `data/path_analysis_by_method.csv`: path classification results

For most replication tasks, you can use these checked-in artifacts directly instead of regenerating them.

## Preparing Defects4J Subjects

The repository already contains `defects4j-subjects-notests/` at the project root. If you want to rebuild the subject checkout from scratch, use:

```console
bash evaluation/setup_d4j-subjects.sh
```

This script clones Defects4J and checks out the fixed versions listed in `evaluation/data/d4j-fixed-version.csv`.

## Regenerating Subject Metadata

The script below analyzes a subject checkout and writes project manifests to `evaluation/defects4j-codefiles/` plus summary rows to `evaluation/subject_statistics.csv`:

```console
python evaluation/compute_statistics.py java
```

In the current repository, the generated manifests and summary CSV are already present, so this step is optional. The checked-in script is mainly useful when refreshing the evaluation artifacts.

## Running Panta on the 130 High-Complexity Classes

The main evaluation driver is `execute_classes_with_high_complexity.py`. It reads `evaluation/data/class_list.csv`, updates per-worker config files, runs Panta through `execute.py`, and records per-class metrics.

Basic usage:

```console
python evaluation/execute_classes_with_high_complexity.py control openai/gpt-4o-mini
```

Useful options:

```console
python evaluation/execute_classes_with_high_complexity.py control openai/gpt-4o-mini --workers 1
python evaluation/execute_classes_with_high_complexity.py control openai/gpt-4o-mini --workers 6
python evaluation/execute_classes_with_high_complexity.py control openai/gpt-4o-mini --rerun
```

Option summary:

- `--workers N`: run the evaluation with `N` parallel workers. Each worker gets its own temporary config file and metrics CSV, and the project list is distributed so the workload is reasonably balanced. Use `--workers 1` for sequential execution, or a larger value such as `--workers 6` for parallel execution.
- `--rerun`: rerun classes that already have an existing HTML result instead of skipping them. Without this flag, the script resumes from the current state and only processes classes that do not yet have a report.

Current behavior of this runner:

- reads the 130 target classes from `evaluation/data/class_list.csv`
- writes HTML reports under `result-files/{prompt}_{sanitized_model}/`
- writes metrics CSV files under `evaluation/data/metrics_{prompt}_{sanitized_model}*.csv`
- creates temporary worker configs `src/panta/config_worker_*.ini` during parallel execution
- skips classes that already have an HTML report unless `--rerun` is provided

Model names are sanitized for output paths, so a model such as `openai/gpt-4o-mini` writes to:

```text
result-files/control_openai_gpt-4o-mini/
```

The current evaluation runner writes configs with:

- `enable_symbolic_execution = false`
- `enable_LLM_path_solving = false`
- `enable_LLM_verify = false`

If you want a different evaluation setting, update the config-writing logic in `execute_classes_with_high_complexity.py`.

## Running SymPrompt

To run the SymPrompt baseline on the same target classes:

```console
python evaluation/execute_symprompt.py symprompt openai/gpt-4o-mini
```

This writes reports under:

```text
result-files/symprompt_openai_gpt-4o-mini/
```

## Path Analysis

To classify extracted CFG paths into pure numerical paths versus object-related paths for the selected target classes:

```console
python evaluation/extract_paths_and_analyze.py
```

This generates:

- `evaluation/data/path_analysis_by_class.csv`
- `evaluation/data/path_analysis_by_method.csv`

## Parsing Coverage and Pass-Rate Results

The evaluation directory also includes post-processing scripts for turning HTML reports into summary CSV files:

```console
python evaluation/result-html-parser.py
python evaluation/result-parser-different-models.py
python evaluation/extract_pass_rate.py
```

These scripts are useful for reproducing the checked-in summary tables such as:

- `evaluation/data/coverage_statistics.csv`
- `evaluation/data/coverage_statistics_models.csv`
- `evaluation/data/pass_rate_statistics.csv`

Some of these post-processing scripts still assume specific result-directory names or hard-coded local paths from the experiment setup. If you run new experiments with different folder names or models, update those paths in the scripts before re-running them.

## Notes

- `data/class_list.csv` currently contains 130 target classes.
- `result-files/` lives at the repository root, not inside `evaluation/`.
- The evaluation scripts assume the project root already contains `defects4j-subjects-notests/` and the main Panta code under `src/panta/`.

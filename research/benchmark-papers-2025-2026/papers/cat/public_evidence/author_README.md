# CAT 

This repository contains the replication artifact for the evaluation code used in our paper.
It includes the main evaluation pipeline, the benchmark subjects used in the experiments,
and a standalone static-analysis component used to support path discovery and project analysis.

## Overview

The artifact contains two major parts:

1. `PLRDGEN_qwenDeployed_CAT/`
	The main evaluation code used in the paper. This part contains the evaluation scripts,
	benchmark subjects, and the supporting Python code used to run the experiments.
2. `sootup-callgraph-pathfinder/`
	A standalone static-analysis utility for call-chain extraction and dependency resolution. This component is
	developed around Java 17 and SootUp-based analysis, and is used to support more complex
	projects and future open-source tool releases.

In addition to the artifact used in the paper, we are also developing a more independent toolchain
to better support open-source usage and more complex software projects, with tighter integration of
static analysis utilities.

## Repository Structure

```text
CAT/
├── CAT_PATH_results.csv
├── README.md
├── PLRDGEN_qwenDeployed_CAT/
│   ├── defects4j-subjects/
│   ├── defects4j-subjects-notests/
│   └── panta/
│       ├── evaluation/
│     
└── sootup-callgraph-pathfinder/
	 ├── pom.xml
	 └── src/
```

Key directories and files:

- `PLRDGEN_qwenDeployed_CAT/defects4j-subjects/`: benchmark subjects with tests.
- `PLRDGEN_qwenDeployed_CAT/defects4j-subjects-notests/`: benchmark subjects prepared without tests.
- `PLRDGEN_qwenDeployed_CAT/panta/evaluation/`: evaluation scripts used in the experiments.
- `PLRDGEN_qwenDeployed_CAT/panta/panta/prompt_templates/java_templates/`: Java prompt templates used by the evaluation pipeline.
- `sootup-callgraph-pathfinder/`: static-analysis utility used for context extraction.
- `CAT_PATH_results.csv`: the CAT_path results corresponding to the discussion after Section 4.2.1 in the paper.

## Environment

### Main evaluation code

The main evaluation code is under `PLRDGEN_qwenDeployed_CAT/`. The Python project metadata is in:

- `PLRDGEN_qwenDeployed_CAT/panta/pyproject.toml`

The evaluation scripts are located in:

- `PLRDGEN_qwenDeployed_CAT/panta/evaluation/`

The Python environment can be set up with Poetry, or reproduced based on the dependencies declared
in `pyproject.toml`.

### Static-analysis component

The static-analysis utility is under `sootup-callgraph-pathfinder/`.

Recommended environment:

- Java 17
- Maven
- SootUp-based dependency stack used by the project

To build the standalone jar:

```bash
cd sootup-callgraph-pathfinder
mvn package
```

## Static Analysis Tool Usage

The main usage pattern of the standalone path-finding tool is:

```bash
java -jar /path/to/sootup-callgraph-pathfinder.jar <classpath> <simple_class> <method> <depth> <output_file>
```

Arguments:

- `classpath`: target project classpath used for analysis.
- `simple_class`: the target class name.
- `method`: the target method name.
- `depth`: maximum search depth.
- `output_file`: path to the generated output file.

Example:

```bash
java -jar /path/to/sootup-callgraph-pathfinder.jar \
  /path/to/project/target/classes:/path/to/dependency.jar \
  MyClass \
  targetMethod \
  3 \
  ./call_paths.txt
```

## Evaluation Scripts

All evaluation scripts for the PLRDGEN artifact are placed in:

- `PLRDGEN_qwenDeployed_CAT/panta/evaluation/`

This directory contains the scripts used to:

- collect subject statistics,
- run evaluation over benchmark projects,
- parse generated results,
- compute aggregate metrics used in the paper.

## Prompt Templates

The Java prompt templates used by the PLRDGEN evaluation pipeline are located in:

- `PLRDGEN_qwenDeployed_CAT/panta/panta/prompt_templates/java_templates/`

In particular:

- `test_generation_prompt_with_cg_single.toml`: used for test generation.
- `failed_test_feedback_prompt.toml`: used for failed-test repair and feedback-guided fixing.

## CAT_path Results

`CAT_PATH_results.csv` contains the CAT_path results referenced in the paper after Section 4.2.1.
The file reports per-project averages for the evaluated subjects, including line and branch related
statistics used in the evaluation summary.

## Notes

This repository is released as the evaluation artifact for the paper. The current release focuses on
reproducibility of the reported experiments, while our ongoing tool development aims to provide:

- better support for open-source usage,
- stronger support for more complex projects,
- tighter integration with standalone static-analysis components.

## Acknowledgement

We thank the authors of PANTA for making their project and paper publicly available. Their open-source
repository and research paper have been valuable references for this artifact and our continuing tool
development.

- GitHub repository: https://github.com/PANTA-TestAutomation/Panta
- Paper: https://arxiv.org/abs/2503.13580


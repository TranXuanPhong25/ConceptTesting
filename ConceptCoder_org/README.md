# ConceptCoder: Learning Code Semantics via Concepts for Code Reasoning Tasks


## Create Environement and Install Dependencies

```
conda create -n conceptcoder python=3.8.13
conda activate conceptcoder
pip install -r requirements.txt
```

## How to process data ?

### To annotate concepts for vulnerability detection:

```bash
cd ConceptCoder/code/design_concept
python design_and_annotate_VD_concepts.py <src_file> <dest_file>
```
    
- <src_file>: JSONL file where each entry contains a "func" key with the source code.

- <dest_file>: Output path for the annotated data.

### To annotate concepts for branch prediction,  please follow the following steps.
Step 1: Run TRACED Tool

- We use the TRACED tool to collect execution traces. Follow the instructions in [tracer/README.md](https://github.com/ARiSE-Lab/TRACED_ICSE_24/blob/main/tracer/README.md). to install and run TRACED.

Step 2: Annotate Concepts
- After that, run the following concept annotator script:
```
cd ConceptCoder/code/design_concept
python design_and_annotate_BP_concepts.py
```

Before running, make sure to set the TRACED result directory at lines 35 and 36 of the script. The script will annotate each example and save the output in the TRACED result directory.


### To create robustness data for vulnerability detection, run:

```bash
cd ConceptCoder/code/data_processing
python build_robustness_data.py <src_file> <dest_file>

```
- <src_file\>: The train data split as jsonl format e.g. train.jsonl where each entry contains a "func" key with the source code.

- <dest_file\>: The test data split as jsonl format e.g. train.jsonl where each entry contains a "func" key with the source code.

##  Processed Data

Annotated training and evaluation datasets are provided with this package. The concept are extracted and annoted in our package. Vulnerability detection data will be found under data/VD and branch prediction is under data/BP. 

Vulnerability Detection:

-   {train,test,valid}_concept.jsonl are concept dataset for VD.
-   {train,test,valid}_general.jsonl are general dataset for VD.
-   {train,test,valid}_concept_probing.jsonl are concept probing data for VD
-   test_concept_robusness.jsonl is the robustness file for VD concept dataset


Branch Prediction:

-   {train,test,valid}.jsonl are the dataset to train  conceptcoder for BP.
-   {train,test,valid}_concept_probing.jsonl are concept probing data for BP


## Training and Evaluation 

To train and evaluate the model with and without ConceptCoder, run the following scripts:

### Vulnerability Detection

```bash
cd ConceptCoder/code/concept_learning/VD
bash run_regular_fune_tuning.sh <mode> <model>
bash run_conceptcoder_fune_tuning.sh <mode> <model>
```
Here, <mode\> should be either "train" or "test". <model\> must be one of the following: qwen3b, qwen7b, starcoder3b, starcoder7b, llama3b, llama8b, codellama7b, magicoder, deepseek7b, or codegemma7b

### Branch Prediction:

```bash
cd ConceptCoder/code/concept_learning/BP
bash run_regular_fune_tuning.sh <mode> <model>
bash run_concept_coder_fune_tuning.sh <mode> <model>
```


## Concept Probing through linear probing

Step 1: Collect the representation first
- Vulnerability detection

```bash
cd ConceptCoder/code/concept_learning/VD
bash run_regular_fune_tuning.sh repr <model> <dataset>
bash run_conceptcoder_fune_tuning.sh repr <model> <dataset>
....
```
Dataset is either concept or general

- Branch Prediction

```bash
cd ConceptCoder/code/concept_learning/BP
bash run_regular_fune_tuning.sh repr <model>
bash run_conceptcoder_fune_tuning.sh repr <model>
....
```

Step 2: Train linear classifier on the representation:


```bash
cd ConceptCoder/code/concept_probing/
bash run_linear_classifier_for_concept_probing.sh <model> <task> <setting> <dataset>
....
```

The <task\> is either "BP" or "VD". Setting is one of the following: fine_tune_baseline, conceptcoder
For VD, dataset is either concept or general. For BP, the dataset is empty "".
# Overview
The `result` folder contains the previously generated results, which you can use directly.
To directly use the results I previously extracted, you need to copy the result files: `cp ./results/* ./`.
This allows you to skip to the next step `get_api_reference`. 

If you prefer to re-analyze the data yourself, proceed with the following steps.

# Prepare 
## Download Pytorch
the source code of Pytorch
```
    git clone https://github.com/pytorch/pytorch
```
## Install the correct version of `clang`
For example, if you have clang-14 in your environment, you should run `pip install clang==14`

# Extract the check requirements from source codes
## Prepare
Define `features` and `target_directory` in the `analyze_torch.py`:
1. `features`: The CHECK FUNCTION NAME that you want to analyze
2. `target_directory`: The source code path of Pytorch

## Run
```
python analyze_torch.py
```
Then, we will get a `all_mutators.json` file. 

# Transfer the check requirements to mutators
```
python cluster.py
```
Then, we will get a `all_clusters.json` file which records the cluster results of all mutators.

```
python torch_mutator_infer.py
```
Then, we will get a `unique_mutators.json` which records the generated mutators.

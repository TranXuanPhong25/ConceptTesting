"""
Standalone inference script: load a fine-tuned model and run inference on
the exception-oracle subset of a dataset, reporting mean/variance/std across
runs.

No training; just deterministic beam-search inference on held-out data,
restricted to rows whose gold target is the literal "exception" marker.
"""

import pickle
import os
import torch
import csv
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import logging as hf_logging
from accelerate import Accelerator
import numpy as np
from datetime import timedelta
from accelerate import InitProcessGroupKwargs
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel

# ===================================================================
# CONFIG -- edit these before running
# ===================================================================
#/scratch/ANONYMIZED/ASE-26-MR/models/codeLlama-7B_tc_mut_doc
CHECKPOINT_DIR = "/scratch/ANONYMIZED/ASE-26-MR/models/codeLlama-7B_tc_mut_doc"
DATASET_PATH = "/scratch/ANONYMIZED/ASE-26-MR/input_data/SF110/dataset_codeLlama-7B_docskip.pickle"
DATASET_VARIANT = "tc_mut_doc"
OUTPUT_DIR = "/scratch/ANONYMIZED/ASE-26-MR/output_data/doc2oracll-SF110"
m_len=700

# Dataset prep builds each split as:
#   {key: tc_mut_doc[key][start:end] for key in ('inputs', 'outputs', 'id')}
# 'outputs' holds the gold target, but it's already a list of token IDs at
# this stage (not a plain string) -- BatchDecodingDataset later does
# torch.LongTensor(inputs + outputs). So filtering must decode via the
# tokenizer before comparing to "exception".
TARGET_KEY = "outputs"

# Inference config
INFERENCE_BATCH_SIZE = 10
BACKBONE_FOR_TOKENIZER = 'codellama/CodeLlama-7b-hf'  # needed to load tokenizer

# ===================================================================
os.environ["NCCL_P2P_DISABLE"] = "1"
os.environ["NCCL_IB_DISABLE"] = "1"

process_group_kwargs = InitProcessGroupKwargs(timeout=timedelta(seconds=5400))
accelerator = Accelerator(kwargs_handlers=[process_group_kwargs])

hf_logging.set_verbosity_error()
torch.manual_seed(7)


# ===================================================================
# Filtering helper
# ===================================================================
def filter_to_exception_rows(data_dict, tokenizer, target_key=TARGET_KEY):
    """
    Keep only rows whose gold target decodes to the literal 'exception'
    marker, so inference only runs on exception-oracle examples.

    data_dict[target_key] is a list of token-ID sequences (not strings),
    so each row is decoded via the tokenizer before comparison. This
    mirrors exactly how eval_model derives `target` from `labels`
    (labels[j][labels[j] != -100] is just the outputs token IDs, since
    BatchDecodingDataset builds labels as [-100]*len(inputs) + outputs).

    Assumes data_dict values are parallel lists (same length, same order).
    """
    keep_idx = []
    for i, out_ids in enumerate(data_dict[target_key]):
        text = tokenizer.decode(out_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        if text.strip() == "exception":
            keep_idx.append(i)
    return {k: [v[i] for i in keep_idx] for k, v in data_dict.items()}


# ===================================================================
# Helpers (same as in training script)
# ===================================================================
def exception_oracle_accuracy(match_array):
    """
    match_array entries are (id_, target, output, match). Since the dataset
    is already restricted to exception-oracle rows, this is just the mean
    of the match flags. Guards against an empty match_array (e.g. if a
    filtered split ended up with zero rows).
    """
    if not match_array:
        return float('nan')
    print(sum(m[3] for m in match_array), len(match_array))    
    return sum(m[3] for m in match_array) / float(len(match_array))


# ===================================================================
# Dataset loaders (copy from training script for compatibility)
# ===================================================================
from dataset_bf import BatchDecodingDataset, batch_decoding_collator


# ===================================================================
# Inference function (same as in training script)
# ===================================================================
def eval_model(data_loader, model, tokenizer, eos_token_id, N):
    model.eval()
    exact_match = torch.tensor([1]).cuda()
    match_array = []
    for i, data in enumerate(data_loader):
        with torch.no_grad():
            labels = data['labels'].cuda()
            input_ids = data['input_ids'].cuda()
            attention_mask = data['attention_mask'].cuda()
            id = data['id']

            outputs = accelerator.unwrap_model(model).generate(
                input_ids, attention_mask=attention_mask, max_new_tokens=300, num_beams=5, num_return_sequences=1,
                early_stopping=False, pad_token_id=eos_token_id, eos_token_id=eos_token_id
            )

            for j in range(input_ids.size(0)):
                output = tokenizer.decode(outputs[j][input_ids.size(1): ], skip_special_tokens=True, clean_up_tokenization_spaces=True)
                target = tokenizer.decode(labels[j][labels[j] != -100], skip_special_tokens=True, clean_up_tokenization_spaces=True)
                id_ = id[j]

                match = 0
                #print(output, target)
                if output.strip() == target.strip():
                    match = 1
                    exact_match[0] += 1

                match_array += [(id_, target.strip(), output.strip(), match)]

    total_match = accelerator.gather_for_metrics(exact_match)
    print(total_match)
    return np.sum(total_match.cpu().numpy()) / N, match_array


# ===================================================================
# Main inference
# ===================================================================
def main():
    print("loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BACKBONE_FOR_TOKENIZER)

    eos_token = tokenizer.special_tokens_map.get("eos_token") or tokenizer.special_tokens_map.get("sep_token")
    eos_token_id = tokenizer.convert_tokens_to_ids(eos_token)
    print(f"EOS token: {eos_token} (id={eos_token_id})")

    print(f"loading fine-tuned model from {CHECKPOINT_DIR}...")
    #model = AutoModelForCausalLM.from_pretrained(CHECKPOINT_DIR)
    base_model = AutoModelForCausalLM.from_pretrained(BACKBONE_FOR_TOKENIZER)
    model = PeftModel.from_pretrained(base_model, CHECKPOINT_DIR).cuda()

    print("loading inference dataset...")
    with open(DATASET_PATH, 'rb') as f:
        loaded_data = pickle.load(f)

    # Unpack the variant (could be 3-element [test, valid, train] or 4-element [test_no_throw, test, valid, train])
    variant_data = loaded_data[DATASET_VARIANT]
    if len(variant_data) == 4:
        test_no_throw, test, valid, train = variant_data
    
    elif len(variant_data) == 3:
        test, valid, train = variant_data
        test_no_throw = None


    if len(variant_data) == 2:  #for OE25 as its all for testing 
        test_no_throw, test = variant_data

    print(f"before filtering: test={len(test['inputs'])} test_no_throw={len(test_no_throw['inputs']) if test_no_throw else 'N/A'}")

    # Restrict to exception-oracle rows only.
    test = filter_to_exception_rows(test, tokenizer)
    if len(test['inputs']) == 0:
        raise ValueError(
            "No exception-oracle rows found in test set after filtering — "
            "check TARGET_KEY matches the dataset's actual target field name."
        )

    if test_no_throw:
        test_no_throw = filter_to_exception_rows(test_no_throw, tokenizer)
        # A dict with empty-list values is still truthy, so re-check length
        # here rather than relying on `if test_no_throw:` later in this
        # function -- otherwise an all-filtered-out split would silently
        # build a 0-row DataLoader and eval_model would divide by N=0.
        if len(test_no_throw['inputs']) == 0:
            print("test_no_throw had 0 exception-oracle rows after filtering; skipping it.")
            test_no_throw = None

    print(f"after filtering:  test={len(test['inputs'])} test_no_throw={len(test_no_throw['inputs']) if test_no_throw else 'N/A'}")

    test_dataset = BatchDecodingDataset(test, max_len=m_len)
    test_loader = torch.utils.data.DataLoader(
        dataset=test_dataset, batch_size=INFERENCE_BATCH_SIZE, shuffle=False, collate_fn=batch_decoding_collator
    )

    if test_no_throw:
        test_no_throw_dataset = BatchDecodingDataset(test_no_throw, max_len=m_len)
        test_no_throw_loader = torch.utils.data.DataLoader(
            dataset=test_no_throw_dataset, batch_size=INFERENCE_BATCH_SIZE, shuffle=False, collate_fn=batch_decoding_collator
        )
    else:
        test_no_throw_dataset = None
        test_no_throw_loader = None

    model = accelerator.prepare(model)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ===================================================================
    # N x inference on test and (if available) test_no_throw
    # ===================================================================
    N_INFER_RUNS = 3

    def run_n_times(data_loader, dataset, n_runs=N_INFER_RUNS):
        accs = []
        all_runs = []
        for r in range(n_runs):
            _, match_array_r = eval_model(data_loader, model, tokenizer, eos_token_id, len(dataset))
            acc = exception_oracle_accuracy(match_array_r)
            accs.append(acc)
            all_runs.append(match_array_r)
            print('  exception-oracle run {}/{}: accuracy={}'.format(r + 1, n_runs, acc))
        return accs, all_runs

    print('=== test: {}x inference, exception-oracle accuracy ==='.format(N_INFER_RUNS))
    test_exc_accs, test_all_runs = run_n_times(test_loader, test_dataset)

    test_mean, test_var = np.nanmean(test_exc_accs), np.nanvar(test_exc_accs)
    test_std = np.nanstd(test_exc_accs)

    print('test exception-oracle:          per-run={} mean={} var={} std={}'.format(test_exc_accs, test_mean, test_var, test_std))

    # if test_no_throw is available, run on that too
    if test_no_throw_loader:
        print('=== test_no_throw: {}x inference, exception-oracle accuracy ==='.format(N_INFER_RUNS))
        test_no_throw_exc_accs, test_no_throw_all_runs = run_n_times(test_no_throw_loader, test_no_throw_dataset)

        ntw_mean, ntw_var = np.nanmean(test_no_throw_exc_accs), np.nanvar(test_no_throw_exc_accs)
        ntw_std = np.nanstd(test_no_throw_exc_accs)

        print('test_no_throw exception-oracle: per-run={} mean={} var={} std={}'.format(test_no_throw_exc_accs, ntw_mean, ntw_var, ntw_std))
    else:
        test_no_throw_exc_accs = None
        test_no_throw_all_runs = None
        ntw_mean = ntw_var = ntw_std = None

    # ===================================================================
    # Log results
    # ===================================================================
    results_txt = os.path.join(OUTPUT_DIR, 'inference_exception_oracle_results.txt')
    with open(results_txt, 'w') as f:
        f.write('=== INFERENCE RESULTS ===\n')
        f.write(f'checkpoint: {CHECKPOINT_DIR}\n')
        f.write(f'dataset: {DATASET_PATH}\n')
        f.write(f'variant: {DATASET_VARIANT}\n\n')
        f.write(f'after filtering:  test={len(test['inputs'])} test_no_throw={len(test_no_throw['inputs']) if test_no_throw else 'N/A'}\n\n')
        f.write('test per-run accuracies: {}\n'.format(test_exc_accs))
        f.write('test mean: {}, variance: {}, std: {}\n'.format(test_mean, test_var, test_std))
        if test_no_throw_exc_accs is not None:
            f.write('test_no_throw per-run accuracies: {}\n'.format(test_no_throw_exc_accs))
            f.write('test_no_throw mean: {}, variance: {}, std: {}\n'.format(ntw_mean, ntw_var, ntw_std))

    print(f"\nresults written to {results_txt}")

    # Pickle all run details
    results_pkl = os.path.join(OUTPUT_DIR, 'inference_exception_oracle_records.pickle')
    with open(results_pkl, 'wb') as f:
        pickle.dump({
            'checkpoint': CHECKPOINT_DIR,
            'dataset': DATASET_PATH,
            'variant': DATASET_VARIANT,
            'test_runs': test_all_runs,
            'test_exception_accuracies': test_exc_accs,
            'test_mean_var_std': (test_mean, test_var, test_std),
            'test_no_throw_runs': test_no_throw_all_runs,
            'test_no_throw_exception_accuracies': test_no_throw_exc_accs,
            'test_no_throw_mean_var_std': (ntw_mean, ntw_var, ntw_std),
        }, f)

    print(f"records written to {results_pkl}")


if __name__ == "__main__":
    main()
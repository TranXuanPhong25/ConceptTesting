import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0,3"
import sys
import argparse
import time
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, LlamaTokenizer, LlamaForCausalLM, LlamaConfig
import pandas as pd
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", default=None, type=str, required=True, help="The model directory.")
    parser.add_argument("--input_dir", default=None, type=str, required=True, help="The input directory.")
    parser.add_argument("--output_dir", default=None, type=str, required=True, help="The output directory where the model predictions and checkpoints will be written.")
    parser.add_argument("--max_new_tokens", default=128, type=int)
    parser.add_argument("--no_repeat_ngram_size", default=5, type=int)

    args = parser.parse_args()

    model_name = args.model_name
    model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.add_special_tokens({"pad_token": "<PAD>",})
    model.resize_token_embeddings(model.config.vocab_size + 1)
    
    data_file = args.input_dir
    df = pd.read_csv(data_file)
    if 'Unnamed: 0' in df.columns:
        df = df.drop(['Unnamed: 0'], axis=1)
    data = df.to_dict("records")
    start = time.perf_counter()
    output_data = []
    print("The number of all dataset: ", len(data), flush=True)
    idx = 0
    for item in data:
        idx += 1
        if idx%100==0:
            print(idx, flush=True)
        fm = item['trigger_fm']
        src_fm = 'Focal method: ' + fm + '\n Test case: '
        project_id = item['project_id']
        bug_id = item['bug_id']
        inputs = tokenizer(src_fm, return_tensors="pt").input_ids
        inputs = inputs.cuda()
        with torch.no_grad():
            outputs = model.generate(inputs, max_new_tokens=256, no_repeat_ngram_size=5, early_stopping=True)
            #outputs = model.generate(inputs, max_new_tokens=512, repetition_penalty=1.1, do_sample=True, top_k=50, top_p=0.95)
        generation = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
        #print("" + 100 *'-')
        #print(generation)
        #print("" + 100 *'-')
        output_data.append([project_id, bug_id, fm, generation])
    output_df = pd.DataFrame(output_data, columns=['project_id', 'bug_id', 'src_fm', 'target_generated'])
    output_df.to_csv(args.output_dir, index=False)
    print(f"Done in {time.time() - start:.2f}s")
    print("finish...")

if __name__ == "__main__":
    main()

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "2,3,4,5,6,7"
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel
import torch
import argparse

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model_name_or_path", type=str, default="../models/codellama7B")
    parser.add_argument("--peft_model_path", type=str, default="../checkpoints/checkpoint_codellama_7b_filter")
    parser.add_argument("--push_to_hub", action="store_true", default=False)

    return parser.parse_args()

def main():
    args = get_args()

    base_model = AutoModelForCausalLM.from_pretrained("../models/codellama7B",
        return_dict=True,
        torch_dtype=torch.float16 
    )

    model = PeftModel.from_pretrained(base_model, args.peft_model_path)
    model = model.merge_and_unload()

    tokenizer = AutoTokenizer.from_pretrained("../models/codellama7B")
    print("finish loading the model and tokenizer...")
    
    model.save_pretrained(f"{args.peft_model_path}-merged")
    tokenizer.save_pretrained(f"{args.peft_model_path}-merged")
    print(f"Model saved to {args.peft_model_path}-merged")

if __name__ == "__main__" :
    main()

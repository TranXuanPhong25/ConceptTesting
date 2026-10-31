import argparse
import torch
from src.pretrained.ModelClasses import ModelClasses
from src.server.Server import Server
from src.parser.ArgumentParser import ArgumentParser


def setup_model(
        model_type: str,
        tokenizer_name: str,
        model_name_or_path: str
):
    _, model_class, tokenizer_class = ModelClasses.getModelClass(model_type)
    # Setup tokenizer
    tokenizer = tokenizer_class.from_pretrained(tokenizer_name)
    tokenizer.add_bos_token = False
    tokenizer.add_eos_token = False
    tokenizer.add_special_tokens({"pad_token": "<pad>"})
    # Setup model
    # Creates a model with uninitialized weights, minimizing memory usage
    pt_model = model_class.from_pretrained(
        model_name_or_path,
        torch_dtype=torch.float16,
    )
    pt_model.resize_token_embeddings(len(tokenizer))
    pt_model.to(device)
    return pt_model, tokenizer


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser()
    ArgumentParser.add_server_arguments(parser)
    args = parser.parse_args()
    device = "cpu"
    # Connect to device
    if torch.cuda.is_available():
        print(f'There are {torch.cuda.device_count()} GPU(s) available.')
        # Set the gpu as device to perform the training
        device = torch.device("cuda:0")
        print(f'Selected GPU: {torch.cuda.get_device_name(0)}')
    else:
        print('No GPU available, using the CPU instead.')
    # Setup model
    model, tokenizer = setup_model(
        args.model_type,
        args.tokenizer_name,
        args.model_name_or_path
    )
    # Instantiate server
    server = Server(
        device,
        model,
        tokenizer,
        args.max_src_length,
        args.max_tgt_length
    )
    # Run server
    server.run(args.port)

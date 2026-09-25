import os
import json
import logging
import argparse

import pickle

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import DataLoader, TensorDataset
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)

class LogisticRegressionModel(nn.Module):
    def __init__(self, input_dim, n_output):
        super(LogisticRegressionModel, self).__init__()
        self.linear = nn.Linear(input_dim, n_output)  # Single-layer model
        self.sigmoid = nn.Sigmoid()  # Apply sigmoid activation

    def forward(self, x):
        return self.linear(x)  # Logistic regression formula

def read_jsonl(path):
    f = open(path, "r")
    data = [json.loads(ex) for ex in f]
    f.close()
    return data


def calculate_metrics(labels, preds, average="binary"):
    acc = accuracy_score(labels, preds)
    prec = precision_score(labels, preds, average=average, zero_division=0)
    recall = recall_score(labels, preds, average=average, zero_division=0)
    f1 = f1_score(labels, preds, average=average, zero_division=0)
    # TN, FP, FN, TP = confusion_matrix(labels, preds).ravel()
    # tnr = TN/(TN+FP)
    # fpr = FP/(FP+TN)
    # fnr = FN/(TP+FN)
    return round(acc,4)*100, round(prec,4)*100, \
        round(recall,4)*100, round(f1,4)*100

# def calculate_metrics(labels, preds, average="binary"):
#     acc = accuracy_score(labels, preds)
#     prec = precision_score(labels, preds, average=average, zero_division=0)
#     recall = recall_score(labels, preds, average=average, zero_division=0)
#     f1 = f1_score(labels, preds, average=average, zero_division=0)
#     # TN, FP, FN, TP = confusion_matrix(labels, preds).ravel()
#     # tnr = TN/(TN+FP)
#     # fpr = FP/(FP+TN)
#     # fnr = FN/(TP+FN)
#     return round(acc,4)*100, round(prec,4)*100, \
#         round(recall,4)*100, round(f1,4)*100

def build_data(args, data_, batch_size=32, shuffle=False):
    X = torch.tensor(np.array([x[0] for x in data_]), dtype=torch.float32)
    Y = torch.tensor([x[1] for x in data_])
    dataset = TensorDataset(X, Y)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
    return dataloader

def train_model(args, model):
    train_dataloader = build_data(args, args.train_data, args.batch_size, shuffle=True)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    best_metric = {
        "f1": 0,
        "acc": 0
    }
    # Training loop
    num_epochs = args.num_epochs
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0

        for batch_X, batch_y in train_dataloader:
            inputs = batch_X.to(args.device)
            targets = batch_y.to(args.device)

            optimizer.zero_grad()  # Reset gradients
            logits = model(inputs)  # Forward pass
            # print(logits, targets)
            loss = criterion(logits, targets.float())  # Compute loss
            loss.backward()  # Backpropagation
            optimizer.step()  # Update weights

            total_loss += loss.item()
        
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {total_loss:.4f}")
        
        valid_dataloader = build_data(args, args.valid_data, args.batch_size, shuffle=False)
        result = test_neural_classifier(args, model, valid_dataloader)
        for metric in ("f1", "acc"):
            # print(result[f"eval_{metric}"] )
            if result[f"eval_{metric}"] > best_metric[metric]:
                best_metric[metric] = result[f"eval_{metric}"]
                logger.info("  "+"*"*20)
                logger.info(f"  Best {metric}:%s",round(best_metric[metric],4))
                logger.info("  "+"*"*20)

                checkpoint_prefix = f'checkpoint-best-{metric}/'
                output_dir = os.path.join(args.model_saved_dir, '{}'.format(checkpoint_prefix))
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                model_to_save = model.module if hasattr(model,'module') else model
                output_dir = os.path.join(output_dir, f'model.bin')
                torch.save(model_to_save.state_dict(), output_dir)
                logger.info(f"Saving best {metric} model checkpoint at epoch {epoch} to {output_dir}")

def test_neural_classifier(args, model, dataloader):
    model.eval()
    logits, labels = [], []
    for batch in dataloader:
        input = batch[0].to(args.device)
        label = batch[1].to(args.device)
        with torch.no_grad():
            logit = F.sigmoid(model(input))
            logit = (logit >= 0.5).int()
            # print(logit.shape)
            logits.append(logit.cpu().numpy())
            labels.append(label.cpu().numpy())
    logits=np.concatenate(logits,0)
    labels=np.concatenate(labels,0)
    # logits = torch.argmax(logits, dim=1)

    print(labels.shape, logits.shape)

    eval_acc, eval_prec, eval_recall, eval_f1 = calculate_metrics(labels, logits, average="macro")
    result = {
        "eval_acc": eval_acc,
        "eval_prec": eval_prec,
        "eval_recall": eval_recall,
        "eval_f1": eval_f1
    }
    return result

def read_representations(args, file=None, data=None):
    if args.statement_level == True:
        repr_data = []
        with open(f"{args.repr_dir}/{file}.pkl", "rb") as f:
            repr_t = pickle.load(f)
            # print(repr_t)
            for x, y in zip(repr_t["repr"], repr_t["label"]):
                repr_data.append((x, y))
    else:
        repr_data = []
        for ex in data:
            with open(f"{args.repr_dir}/{file}/{ex['idx']}.pkl", "rb") as f:
                repr_t = pickle.load(f)
                repr_data.append((repr_t['repr'], ex['concepts']))
    return repr_data

def main(args):
    
    train_data = read_jsonl(args.train_data_file)
    valid_data = read_jsonl(args.eval_data_file)
    test_data = read_jsonl(args.test_data_file)
    train, test, valid = [], [], []


    train_data_file = args.train_data_file.split("/")[-1].split(".")[0]
    train = read_representations(args, train_data_file, train_data)
    args.input_size = len(train[0][0])
    args.n_output = len(train[0][1])
    # with open(f"{args.repr_dir}/{train_data_file}.pkl", "rb") as f:
    #     repr_t = pickle.load(f)
    #     # print(repr_t)
    #     for x, y in zip(repr_t["repr"], repr_t["labs"]):
    #         # print(x)
    #         # print(y)
    #         train.append((x, y))
    #         # print(x.shape)
    #         args.input_size = len(x)
    
    # return
    valid_data_file = args.eval_data_file.split("/")[-1].split(".")[0]
    valid = read_representations(args, valid_data_file, valid_data)
    test_data_file = args.test_data_file.split("/")[-1].split(".")[0]
    test = read_representations(args, test_data_file, test_data)

    print("Train data size: ", len(train))
    print("Valid data size: ", len(valid))
    print("Test data size: ", len(test))
    args.train_data = train
    args.valid_data = valid
    args.test_data = test
    if args.do_train:
        model = LogisticRegressionModel(args.input_size, args.n_output)
        model.to(args.device)
        train_model(args, model)

    if args.do_eval:
        test_dataloader = build_data(args, args.valid_data, args.batch_size, shuffle=False)

        model = LogisticRegressionModel(args.input_size, args.n_output)
        model.to(args.device)

        checkpoint_prefix = f'checkpoint-best-f1/'
        output_dir = os.path.join(args.model_saved_dir, '{}'.format(checkpoint_prefix))
        model_to_save = model.module if hasattr(model,'module') else model
        output_dir = os.path.join(output_dir, f'model.bin')

        logger.info(f"Loading checkpoint: {output_dir}")
        model.load_state_dict(torch.load(output_dir))
        model.to(args.device)
        result = test_neural_classifier(args, model, test_dataloader)
        print("Concept: ",  "Result: ", result)

    if args.do_test:
        test_dataloader = build_data(args, args.test_data, args.batch_size, shuffle=False)

        model = LogisticRegressionModel(args.input_size, args.n_output)
        model.to(args.device)

        checkpoint_prefix = f'checkpoint-best-f1/'
        output_dir = os.path.join(args.model_saved_dir, '{}'.format(checkpoint_prefix))
        model_to_save = model.module if hasattr(model,'module') else model
        output_dir = os.path.join(output_dir, f'model.bin')

        logger.info(f"Loading checkpoint: {output_dir}")
        model.load_state_dict(torch.load(output_dir))
        model.to(args.device)
        result = test_neural_classifier(args, model, test_dataloader)
        print("Concept: ",  "Result: ", result)

import argparse
import sys
import torch

# model="Qwen2.5-Coder-3B"
# project= "bpft_grad_2_trbatch_16_sample_all_part_1_wo_sptok_end_stmt_class_train_concept_seed_1"
# data_dir="../../data/dataset/codenet/branch_only_concept"
# repr_dir=f"../../data/representation/branch_prediction/{model}/{project}/"
# model_saved_dir= f"../../data/saved_models/linear_classifier/branch_prediction/{model}/{project}/"
# # Simulate CLI arguments in the notebook
# sys.argv = [
#     "notebook",  # dummy script name
#     "--classifier_type", "neural",
#     "--project", project,
#     "--model_type", model,
#     "--train_data_file", f"{data_dir}/train_qun_con_wal1bwl512_statements_class_bal_ratio_part_2.jsonl",
#     "--eval_data_file", f"{data_dir}/valid_qun_con_wal1bwl512_statements_class_bal_ratio_part_2.jsonl",
#     "--test_data_file", f"{data_dir}/test_qun_con_wal1bwl512_statements_class_bal_ratio_part_2.jsonl",
#     "--input_size", "2048",
#     "--model_saved_dir",model_saved_dir,
#     "--do_train",
#     "--do_eval",
#     "--do_test",
#     "--metric", "f1",
#     "--num_epochs", "100",
#     "--batch_size", "64",
#     "--repr_dir", repr_dir,
#     "--concept_target_index", "64",
# ]

# Set up the parser
parser = argparse.ArgumentParser()
parser.add_argument("--classifier_type", default="neural", type=str)
parser.add_argument("--project", default="parallel_primevul_cls", type=str)
parser.add_argument("--model_type", default="Qwen2.5-Coder-3B", type=str)
parser.add_argument("--dataset", default="primevul", type=str)
parser.add_argument("--train_data_file", default="train_null_check.jsonl", type=str)
parser.add_argument("--eval_data_file", default="valid_null_check.jsonl", type=str)
parser.add_argument("--test_data_file", default="test_null_check.jsonl", type=str)
parser.add_argument("--input_size", default=2048, type=int)
parser.add_argument("--model_saved_dir", default="../../data/saved_models/linear_classifier", type=str)
parser.add_argument("--do_train", action='store_true')
parser.add_argument("--do_eval", action='store_true')
parser.add_argument("--do_test", action='store_true')
parser.add_argument("--metric", default="f1", type=str)
parser.add_argument("--num_epochs", default=100, type=int)
parser.add_argument("--batch_size", default=64, type=int)
parser.add_argument("--repr_dir", default="parallel_primevul_cls", type=str)
parser.add_argument("--consider_small_function_only", action='store_true')
parser.add_argument("--concept_target_index", default=64, type=int)
parser.add_argument("--statement_level", action='store_true')

# Parse the arguments
args = parser.parse_args()
args.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Print the parsed arguments
print(args)

main(args)

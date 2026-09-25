# coding=utf-8

from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
os.environ["HF_ENDPOINT"] = "https://huggingface.co"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import random
import math
import pickle
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, SequentialSampler
from torch.utils.data.distributed import DistributedSampler
import json
from torch.nn.utils.rnn import pack_padded_sequence


from tqdm import tqdm, trange
import multiprocessing

cpu_cont = multiprocessing.cpu_count()
from transformers import (WEIGHTS_NAME, AdamW, get_linear_schedule_with_warmup, BitsAndBytesConfig, 
                        LlamaConfig, LlamaModel, CodeLlamaTokenizer,
                        Starcoder2Config, Starcoder2Model, AutoTokenizer,
                        Qwen2Config, Qwen2Model, Qwen2Tokenizer,
                        AutoConfig, AutoModel, 
                        )
from peft import LoraConfig, TaskType, get_peft_model


from accelerate import Accelerator
from accelerate.logging import get_logger
from accelerate.utils import set_seed

import os

logger = get_logger(__name__)

MODEL_CLASSES = {
    'codellama': (LlamaConfig, LlamaModel, CodeLlamaTokenizer),
    'starcoder': (Starcoder2Config, Starcoder2Model, AutoTokenizer),
    'qwen': (Qwen2Config, Qwen2Model, Qwen2Tokenizer),
    'deepseek': (AutoConfig, AutoModel, AutoTokenizer),
    'magicoder': (AutoConfig, AutoModel, AutoTokenizer),
    'codegemma': (AutoConfig, AutoModel, AutoTokenizer),
    'llama': (AutoConfig, AutoModel, AutoTokenizer),
}
# def set_seed(seed):
#     random.seed(seed)
#     np.random.seed(seed)
#     torch.manual_seed(seed)
#     torch.cuda.manual_seed_all(seed)

#     torch.backends.cudnn.deterministic = True
#     torch.backends.cudnn.benchmark = False
#     os.environ['PYTHONHASHSEED'] = str(seed)


class MultiTaskLoss(nn.Module):
    def __init__(self, num_tasks):
        super().__init__()
        self.log_vars = nn.Parameter(torch.zeros(num_tasks))  # Learnable uncertainties

    def forward(self, losses):
        weighted_losses = [
            (torch.exp(-self.log_vars[i]) * losses[i] + self.log_vars[i]) 
            for i in range(len(losses))
        ]
        return sum(weighted_losses)



def average_pool_by_segments_optimized(A, B, max_segments=4):
    """
    Optimized version using vectorized operations and scatter operations.
    """
    # valid_mask = (B != -1)
    # A = A[valid_mask]
    # B = B[valid_mask]
    # print(A.shape)
    # Check if first or last column has -1 across any batch
    # print(A.shape, B.shape)
    
    # print(A.shape, B.shape)
    bs, seq_len, feat_dim = A.shape
    device = A.device
    
    # Create batch indices for flattening
    batch_indices = torch.arange(bs, device=device).unsqueeze(1).expand(-1, seq_len)
    # print(batch_indices)
    
    # Flatten everything for vectorized processing
    A_flat = A.reshape(-1, feat_dim)  # (bs * seq_len, feat_dim)
    B_flat = B.reshape(-1)            # (bs * seq_len,)
    batch_flat = batch_indices.reshape(-1)
    
    masked = ~(B_flat == -1)
    
    A_flat = A_flat[masked]
    B_flat = B_flat[masked]
    batch_flat = batch_flat[masked]
    
    # (bs * seq_len,)
    # print("bacth", batch_flat)
    
    # Create unique segment IDs across batches
    # This ensures segments from different batches don't get mixed
    max_segments_per_batch = seq_len  # Upper bound
    # print(max_segments_per_batch)
    unique_segment_ids = batch_flat * max_segments_per_batch + B_flat
    # print(unique_segment_ids)
    
    # Get unique segments and their inverse mapping
    unique_segments, inverse_indices = torch.unique(unique_segment_ids, return_inverse=True)
    num_unique_segments = len(unique_segments)
    
    # print("Unique segments:", unique_segments)
    # print("Inverse indices:", inverse_indices)
    
    # Sum features for each unique segment
    segment_sums = torch.zeros(num_unique_segments, feat_dim, device=device, dtype=A_flat.dtype)
    # print("Segment sums:", segment_sums)
    segment_sums.scatter_add_(0, inverse_indices.unsqueeze(1).expand(-1, feat_dim), A_flat)
    # print("Scatter add", segment_sums)
    
    # Count elements in each segment
    segment_counts = torch.zeros(num_unique_segments, device=device, dtype=A_flat.dtype)
    # print("Segment counts: ", segment_counts)
    
    segment_counts.scatter_add_(0, inverse_indices, torch.ones_like(inverse_indices, dtype=A_flat.dtype))
    # print("Segment counts scatter add: ", segment_counts)

    # Average each segment
    segment_averages = segment_sums / segment_counts.unsqueeze(1)
    
    # Map back to batch structure
    batch_ids = unique_segments // max_segments_per_batch
    # print("batch_ids", batch_ids, max_segments_per_batch)
    
    # Count segments per batch
    segments_per_batch = torch.zeros(bs, dtype=torch.long, device=device)
    segments_per_batch.scatter_add_(0, batch_ids, torch.ones_like(batch_ids))
    
    # print("segments_per_batch", segments_per_batch)
    
    # max_len = segments_per_batch.max().item()
    max_len = max_segments
    
    # Create output tensor
    A_pooled = torch.zeros(bs, max_len, feat_dim, device=device, dtype=A_flat.dtype)
    
    # Fill in the averages
    batch_offsets = torch.zeros(bs + 1, dtype=torch.long, device=device)
    batch_offsets[1:] = segments_per_batch.cumsum(0)
    
    # print("Batch offsets: ", batch_offsets)
    
    for i in range(bs):
        start_idx = batch_offsets[i]
        end_idx = batch_offsets[i + 1]
        num_segments = min(end_idx - start_idx, max_len)
        if num_segments > 0:
            A_pooled[i, :num_segments] = segment_averages[start_idx:start_idx + num_segments]
    
    padded_counts = max_len - segments_per_batch.clamp(max=max_len)
    
    return A_pooled, padded_counts, segments_per_batch.clamp(max=max_len)

class DecoderClassifier(nn.Module):
    def __init__(self, encoder, config, tokenizer, args):
        super(DecoderClassifier, self).__init__()
        self.encoder = encoder
        self.config=config
        self.tokenizer=tokenizer
        self.args=args

        self.cbl = nn.Linear(config.hidden_size, self.args.concepts)
        self.relu = nn.ReLU()
        self.classifier = nn.Linear(self.args.concepts, 2)
        # if self.args.train_concept:
        #     self.classifier1 = nn.Linear(config.hidden_size, self.args.concepts)
        #     self.loss_sum = MultiTaskLoss(2)
  

    # def forward(self, input_ids=None, labels=None, concept_labels=None, weight=None, return_representation=False, vul_weight=1, concept_weight=0.005):
    def forward(self, input_ids=None, labels=None, concept_labels=None, tok_to_line_map=None, weight=None, return_representation=False, vul_weight=1, concept_weight=0.50, epoch=0):
        attention_mask = input_ids.ne(self.tokenizer.pad_token_id)
        outputs = self.encoder(input_ids, attention_mask=attention_mask)
        hidden_states = outputs[0]

        # logits = self.classifier(hidden_states)

        batch_size = input_ids.size(0)
        if self.config.pad_token_id is None and batch_size != 1:
            raise ValueError("Cannot handle batch sizes > 1 if no padding token is defined.")
        if self.config.pad_token_id is None:
            sequence_lengths = -1
        else:
            if input_ids is not None:
                # if no pad token found, use modulo instead of reverse indexing for ONNX compatibility
                sequence_lengths = torch.eq(input_ids, self.config.pad_token_id).int().argmax(-1) - 1
                sequence_lengths = sequence_lengths % input_ids.shape[-1]
                sequence_lengths = sequence_lengths.to(hidden_states.device)
            else:
                sequence_lengths = -1


        lines_hidden_states, padded_count, lengths = average_pool_by_segments_optimized(hidden_states, tok_to_line_map, max_segments=self.args.max_statements)
        logits_concept = self.cbl(lines_hidden_states)
        # print("logitsconcept", logits_concept)
        cbl_output = torch.sigmoid(logits_concept)
        mask = torch.arange(logits_concept.shape[1], device=logits_concept.device,dtype=logits_concept.dtype).expand(logits_concept.shape[0], logits_concept.shape[1]) < lengths.unsqueeze(1)
        mask = mask.unsqueeze(-1).float()
        # print("mask", mask)
        x_masked = logits_concept * mask
        # print("x_masked", logits_concept, x_masked)
        mean_x = x_masked.sum(dim=1) / lengths.unsqueeze(1).float()
        mean_x = mean_x.to(dtype=logits_concept.dtype)
        # print(mean_x.shape)
        # print("mean", mean_x, lengths)
        logits = self.classifier(mean_x)
        prob = nn.functional.softmax(logits, dim=-1)

        # print(self.loss_sum.log_vars)
        output = []
        if labels is not None:
            labels = labels.to(logits.device)
            loss_fct = nn.CrossEntropyLoss(weight=weight)
            loss_logit = loss_fct(logits.view(-1, 2), labels.view(-1))

            loss_multilabel = nn.BCEWithLogitsLoss(reduction="mean")
            concept_labels = concept_labels.to(logits_concept.device)
            concept_labels = concept_labels.view(-1, concept_labels.size(-1))
            logits_concept = logits_concept.view(-1, logits_concept.size(-1))

            mask = ~(concept_labels == -1).all(dim=1)
            loss_concept = loss_multilabel(logits_concept[mask], concept_labels[mask].to(torch.bfloat16))
            loss = loss_logit * vul_weight + loss_concept * concept_weight
            output.append(loss)
        output.append(prob)
        output.append(cbl_output)
        if return_representation:
            # representation = hidden_states[torch.arange(batch_size, device=logits.device), sequence_lengths]
            output.append(lines_hidden_states)
        return output


class InputFeatures(object):
    """A single training/test features for a example."""
    def __init__(self,
                 input_tokens,
                 input_ids,
                 idx,
                 label,
                 concept_label,
                 tok_to_line_map

    ):
        self.input_tokens = input_tokens
        self.input_ids = input_ids
        self.idx=idx
        self.label=label
        self.concept_label=concept_label
        self.tok_to_line_map = tok_to_line_map


        
def convert_examples_to_features(js,tokenizer,args):
    code = js['func']
    lines = code.split("\n")
    
    code_tokens = []
    concept_targets = []
    tok_to_line_map = []
    # print(js['lines_concept'])
    for i, line in enumerate(lines):
        snippet = f"{line}\n"
        tokens =tokenizer.tokenize(snippet)
        code_tokens.extend(tokens)
        concept_targets.append(js['lines_concept'][f"{i}"])
        tok_to_line_map.extend([i] * len(tokens))
        if len(code_tokens) > args.block_size:
            break
    if args.model_type in ["starcoder", "qwen"]:
        # code_tokens=tokenizer.tokenize(code)
        source_tokens = code_tokens[:args.block_size]
        tok_to_line_map = tok_to_line_map[:args.block_size]
    else:
        # code_tokens=tokenizer.tokenize(code)
        code_tokens = code_tokens[:args.block_size-2]
        tok_to_line_map = tok_to_line_map[:args.block_size - 2]
        source_tokens =[tokenizer.bos_token]+code_tokens+[tokenizer.eos_token]
        tok_to_line_map = [-1] + tok_to_line_map + [-1]

    source_ids =  tokenizer.convert_tokens_to_ids(source_tokens)
    padding_length = args.block_size - len(source_ids)
    source_ids+=[tokenizer.pad_token_id]*padding_length
    tok_to_line_map += [-1] * padding_length

    concept_targets = concept_targets[:args.max_statements]
    pading_statements = args.max_statements - len(concept_targets)
    concept_targets += [[-1] * len(concept_targets[0]) for i in range(pading_statements)]

    return InputFeatures(source_tokens,source_ids,js['idx'], js[args.target_key], concept_targets, tok_to_line_map)
    # return InputFeatures(source_tokens,source_ids,js['idx'], js[args.target_key], [0, 0, 0, 0])


class TextDataset(Dataset):
    def __init__(self, tokenizer, args, file_path=None):
        self.examples = []
        with open(file_path) as f:
            for line in f:
                js=json.loads(line.strip())
                # if js['project'] == "tensorflow":
                #     continue
                inp_feat = convert_examples_to_features(js,tokenizer,args)
                if inp_feat != None:
                    self.examples.append(inp_feat)

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, i):       
        return torch.tensor(self.examples[i].input_ids), torch.tensor(self.examples[i].label), torch.tensor(self.examples[i].concept_label), torch.tensor(self.examples[i].tok_to_line_map), torch.tensor(self.examples[i].idx)


def train(args, accelerator, train_dataset, eval_dataset, model, tokenizer):
    """ Train the model """
    train_dataloader = DataLoader(train_dataset, shuffle=True, batch_size=args.train_batch_size, num_workers=4)
    args.eval_batch_size = args.per_gpu_eval_batch_size * max(1, args.n_gpu)
    # eval_sampler = SequentialSampler(eval_dataset) if args.local_rank == -1 else DistributedSampler(eval_dataset)
    eval_dataloader = DataLoader(eval_dataset, shuffle=False, batch_size=args.eval_batch_size, num_workers=4)

    num_update_steps_per_epoch = math.ceil(len(train_dataloader) / args.gradient_accumulation_steps)
    args.max_steps = args.epoch*num_update_steps_per_epoch
    args.save_steps = len(train_dataloader)
    args.num_train_epochs = args.epoch
    # model.to(args.device)
    # Prepare optimizer and schedule (linear warmup and decay)

    def freeze_first_k_layers(model, k=5):
        """
        Makes all parameters trainable, then freezes only the first `n-k` transformer layers.
        """
        for param in model.parameters():
            param.requires_grad = True
        layers = model.encoder.layers # adjust if your model structure is different
        for i in range(len(layers) - k):
            for param in layers[i].parameters():
                param.requires_grad = False
        for name, param in model.named_parameters():
            if "embed_tokens" in name:
                param.requires_grad = False
    freeze_first_k_layers(model, 5)

    for name, param in model.named_parameters():
        if param.requires_grad:
            print("✅", name)
        else:
            print("❌", name)


    no_decay = ['bias', 'LayerNorm.weight']
    # if args.model_type in ("codellama", "deepseek"):
    no_decay.append('LlamaRMSNorm.weight')
    optimizer_grouped_parameters = [
        {'params': [p for n, p in model.named_parameters() if p.requires_grad and not any(nd in n for nd in no_decay)],
        'weight_decay': args.weight_decay},
        {'params': [p for n, p in model.named_parameters() if p.requires_grad and any(nd in n for nd in no_decay)], 'weight_decay': 0.0}
    ]
    # print(n)
    # print("optimizer_grouped_parameters", optimizer_grouped_parameters)
    optimizer = AdamW(optimizer_grouped_parameters, lr=args.learning_rate, eps=args.adam_epsilon)
    if args.warmup_steps == 0:
        num_warmup = args.max_steps * args.warmup_ratio
    else:
        num_warmup = args.warmup_steps
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=num_warmup,
                                                num_training_steps=args.max_steps)

    print(args.train_batch_size, accelerator.num_processes, accelerator.gradient_accumulation_steps)
    total_batch_size = args.train_batch_size * accelerator.num_processes * accelerator.gradient_accumulation_steps
    logger.info("***** Running training *****")
    logger.info("  Num examples = %d", len(train_dataset))
    logger.info("  Num Epochs = %d", args.num_train_epochs)
    logger.info("  Instantaneous batch size per GPU = %d", args.train_batch_size)
    logger.info("  Total train batch size (w. parallel, distributed & accumulation) = %d",
                total_batch_size)
    logger.info("  Gradient Accumulation steps = %d", args.gradient_accumulation_steps)
    logger.info("  Total optimization steps = %d", args.max_steps)
    
    tr_loss, logging_loss, avg_loss, tr_nb, tr_num, train_loss = 0.0, 0.0, 0.0, 0, 0, 0
    best_f1=0.0
    best_acc=0.0
    patience = 0

    train_dataloader, eval_dataloader, model, optimizer, scheduler = accelerator.prepare(
        train_dataloader, eval_dataloader, model, optimizer, scheduler
    )

    if args.initial_task != None:
        assert args.initial_task != args.project
        checkpoint_prefix = f'checkpoint-best-f1/{args.initial_task}/{args.model_dir}/'
        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))
        print("loading checkpoints from the path: ", output_dir)
        accelerator.load_state(output_dir)
    
    if args.latest_task != None:
        # assert args.initial_task != args.project
        checkpoint_prefix = f'checkpoint-best-f1/{args.latest_task}/{args.model_dir}'
        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))
        print("loading checkpoints from the path: ", output_dir)
        accelerator.load_state(output_dir, load_module_strict=False, load_optimizer_states=False, load_lr_scheduler_states=False)
        # accelerator.load_state(output_dir, load_module_strict=False, load_module_only=True, load_lr_scheduler_states=False)

    if args.fine_tune_classifier_only:
        optimizer_grouped_parameters = []
        for n, p in model.named_parameters():
            if "classifier"  in n:
                optimizer_grouped_parameters.append(p)
            else:
                p.requires_grad = False
            print("optimizer_grouped_parameters", optimizer_grouped_parameters)
        optimizer = AdamW(optimizer_grouped_parameters, lr=args.learning_rate, eps=args.adam_epsilon)
        scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=num_warmup,
                                                    num_training_steps=args.max_steps)
        train_dataloader, eval_dataloader, model, optimizer, scheduler = accelerator.prepare(
            train_dataloader, eval_dataloader, model, optimizer, scheduler
        )

    model.zero_grad()
    # print(model)
    args.logging_steps = len(train_dataloader) // 2
    step = 0
    for idx in range(args.start_epoch, int(args.num_train_epochs)): 
        bar = tqdm(train_dataloader, total=len(train_dataloader), disable=not accelerator.is_local_main_process)
        tr_num = 0
        train_loss = 0
        logits_lst = []
        labels_lst = []
        torch.cuda.empty_cache() 
        for local_step, batch in enumerate(bar):
            model.train()
            inputs, labels, concept_labels, tok_to_line_map, _ = batch
            with accelerator.accumulate(model):
                output__ = model(
                    inputs, labels, concept_labels, tok_to_line_map, vul_weight=args.vul_weight,
                    concept_weight=args.concept_weight, epoch=idx
                )
                loss, logits = output__[0], output__[1]
                accelerator.backward(loss)
                accelerator.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
            
            logits, labels = accelerator.gather_for_metrics((logits, labels))
            # concept_logits, concept_labels = accelerator.gather_for_metrics((concept_logits, concept_labels))
            # cast to torch.float16
            logits_lst.append(logits.detach().cpu().float().numpy())
            labels_lst.append(labels.detach().cpu().float().numpy())

            step_loss = accelerator.reduce(loss.detach().clone()).item()
            tr_loss += step_loss    
            tr_num += 1
            train_loss += step_loss
            if avg_loss == 0:
                avg_loss = tr_loss
            avg_loss = round(train_loss/tr_num, 5)
            bar.set_description("epoch {} loss {}".format(idx, avg_loss))
            
            if step == 0:
                avg_loss = round(train_loss/tr_num,5)
                # train_acc, train_prec, train_recall, train_f1, train_tnr, train_fpr, train_fnr = calculate_metrics(step_labels_lst, step_preds_lst)
                if args.evaluate_during_training:  # Only evaluate when single GPU otherwise metrics may not average well
                    results = evaluate(args, accelerator, eval_dataloader, eval_dataset, model, tokenizer, eval_when_training=True)
                    for key, value in results.items():
                        logger.info("  %s = %s", key, round(value, 4))                    
            
            ###
            # log after every logging_steps (e.g., 1000)
            ###
            if (step + 1) % args.logging_steps == 0:
                avg_loss=round(train_loss/tr_num,5)
                # train_acc, train_prec, train_recall, train_f1, train_tnr, train_fpr, train_fnr = calculate_metrics(step_labels_lst, step_preds_lst)
                if args.evaluate_during_training:  # Only evaluate when single GPU otherwise metrics may not average well
                    results = evaluate(args, accelerator, eval_dataloader, eval_dataset, model, tokenizer,eval_when_training=True)
                    for key, value in results.items():
                        logger.info("  %s = %s", key, round(value,4))                    
                
                # Save model checkpoint    
                if results['eval_f1']>best_f1:
                    best_f1=results['eval_f1']
                    logger.info("  "+"*"*20)  
                    logger.info("  Best f1:%s",round(best_f1,4))
                    logger.info("  "+"*"*20)                          
                    
                    checkpoint_prefix = f'checkpoint-best-f1/{args.project}/{args.model_dir}'
                    output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))                        
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)    
                    accelerator.save_state(output_dir)
                    logger.info(f"Saving best f1 model checkpoint at epoch {idx} step {step} to {output_dir}")
            
            # increment step within the same epoch
            step += 1
            torch.cuda.empty_cache()

    # writer.close()
    if args.do_test:
        checkpoint_prefix = f'checkpoint-best-f1/{args.project}/{args.model_dir}'
        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))
        accelerator.load_state(output_dir)
        result = test(args, accelerator, model, tokenizer) 
        logger.info("***** Test results *****")
        for key in sorted(result.keys()):
            logger.info("  %s = %s", key, str(round(result[key],4)))              

def calculate_metrics(labels, preds):
    acc=accuracy_score(labels, preds)
    prec = precision_score(labels, preds)
    recall = recall_score(labels, preds)
    f1 = f1_score(labels, preds)
    TN, FP, FN, TP = confusion_matrix(labels, preds).ravel()
    tnr = TN/(TN+FP)
    fpr = FP/(FP+TN)
    fnr = FN/(TP+FN)
    return round(acc,4)*100, round(prec,4)*100, \
        round(recall,4)*100, round(f1,4)*100, round(tnr,4)*100, \
            round(fpr,4)*100, round(fnr,4)*100

def evaluate(args, accelerator, eval_dataloader, eval_dataset, model, tokenizer, eval_when_training=False):
    # Loop to handle MNLI double evaluation (matched, mis-matched)
    eval_output_dir = args.output_dir

    if not os.path.exists(eval_output_dir) and args.local_rank in [-1, 0]:
        os.makedirs(eval_output_dir, exist_ok=True)

    args.eval_batch_size = args.per_gpu_eval_batch_size * max(1, args.n_gpu)

    # Eval!
    logger.info("***** Running evaluation *****")
    logger.info("  Num examples = %d", len(eval_dataset))
    logger.info("  Batch size = %d", args.eval_batch_size)
    
    model.eval()
    losses = []
    logits = [] 
    labels = []
    concept_logits = []
    concept_labels = []
    for batch in eval_dataloader:
        inputs, label, concept_label, tok_to_line_map, _ = batch
        with torch.no_grad():
            # lm_loss,logit, concept_logit = model(inputs,label, concept_label)
            output_ = model(inputs,label, concept_label, tok_to_line_map)
            lm_loss, logit = output_[0], output_[1]
            # if args.train_concept:
            #     concept_logit = output_[2]
        
        losses.append(accelerator.gather_for_metrics(lm_loss.repeat(args.eval_batch_size)))
        logit, label = accelerator.gather_for_metrics((logit, label))
        logits.append(logit.cpu().float().numpy())
        labels.append(label.cpu().float().numpy())

        # if args.train_concept:
        #     concept_logit, concept_label = accelerator.gather_for_metrics((concept_logit, concept_label))
        #     concept_logits.append(concept_logit.cpu().float().numpy())
        #     concept_labels.append(concept_label.cpu().float().numpy())
    
    losses = torch.cat(losses)
    eval_loss = torch.mean(losses)
    logits=np.concatenate(logits,0)
    labels=np.concatenate(labels,0)

    # if args.model_type in set(['codegen', 'starcoder', 'codellama', 'qwen', 'deepseek', 'magicoder', 'codegemma']):
    preds=logits[:,1]>0.5
        # concept_preds = concept_logits[:,1] > 0.5
    # else:
    #     preds=logits[:,0]>0.5
        # concept_preds = concept_logits[:,0] > 0.5
    eval_acc, eval_prec, eval_recall, eval_f1, eval_tnr, eval_fpr, eval_fnr = calculate_metrics(labels, preds)
    perplexity = torch.tensor(eval_loss)
    # concept_eval_acc, concept_eval_prec, concept_eval_recall, concept_eval_f1, concept_eval_tnr, concept_eval_fpr, concept_eval_fnr = calculate_metrics(concept_labels, concept_preds)
    # concept_eval_f1 = f1_score(concept_labels, concept_preds, average="macro")
    result = {
        "eval_loss": float(perplexity),
        "eval_acc": eval_acc,
        "eval_prec": eval_prec,
        "eval_recall": eval_recall,
        "eval_f1": eval_f1,
    }
    # if args.train_concept:
    #     concept_logits = np.concatenate(concept_logits, axis=0).reshape(-1, concept_logits[0].shape[-1])
    #     concept_labels = np.concatenate(concept_labels, axis=0).reshape(-1, concept_labels[0].shape[-1])

    #     # Step 2: Create mask for rows where not all elements are -1
    #     valid_mask = ~(concept_labels == -1).all(axis=1)
    #     # Step 3: Filter out invalid rows
    #     logits_valid = concept_logits[valid_mask]
    #     labels_valid = concept_labels[valid_mask]
    #     # Step 4: Binarize logits
    #     y_pred = (logits_valid > 0.5).astype(int)
    #     y_true = labels_valid.astype(int)
    #     # Step 5: Compute macro F1 score
    #     concept_eval_f1 = f1_score(y_true, y_pred, average="macro")
    #     # Step 6: Save result
    #     result["concept_eval_f1"] = concept_eval_f1

    return result

def load_data(jsonl_path):
    '''
    Load data from jsonl file
    '''
    with open(jsonl_path, 'r') as f:
        data = [json.loads(line.rstrip()) for line in f]
    return data

def analyze_predictions(predictions_path, data_path):
    data = load_data(data_path)
    predictions = []
    with open(predictions_path, 'r') as f:
        for line in f:
            id, pred = line.strip().split('\t')
            id = int(id)
            pred = int(pred)
            predictions.append({"id": id, "pred": pred})
    
    assert len(predictions) == len(data)
    assert len(predictions) % 2 == 0
    num_acc = 0
    num_all_vul = 0
    num_all_sec = 0
    num_reversed = 0
    for i in range(len(predictions) // 2):
        assert predictions[2 * i]['id'] == data[2 * i]['idx']
        assert predictions[2 * i + 1]['id'] == data[2 * i + 1]['idx']
        assert data[2 * i]["commit_id"] == data[2 * i + 1]["commit_id"]
        if predictions[2 * i]['pred'] == data[2 * i]['target'] and predictions[2 * i + 1]['pred'] == data[2 * i + 1]['target']:
            num_acc += 1
        elif predictions[2 * i]['pred'] == predictions[2 * i + 1]['pred'] and predictions[2 * i]['pred'] == 0:
            num_all_sec += 1
        elif predictions[2 * i]['pred'] == predictions[2 * i + 1]['pred'] and predictions[2 * i]['pred'] == 1:
            num_all_vul += 1
        else:
            num_reversed += 1

    print("num_acc: {}".format(num_acc))
    print("num_all_sec: {}".format(num_all_sec))
    print("num_all_vul: {}".format(num_all_vul))
    print("num_reversed: {}".format(num_reversed))


def test(args, accelerator, model, tokenizer):
    # Loop to handle MNLI double evaluation (matched, mis-matched)
    eval_dataset = TextDataset(tokenizer, args, args.test_data_file)
    args.eval_batch_size = args.per_gpu_eval_batch_size * max(1, args.n_gpu)
    eval_dataloader = DataLoader(eval_dataset, shuffle=False, batch_size=args.eval_batch_size)

    eval_dataloader = accelerator.prepare(eval_dataloader)

    logger.info("***** Running Test *****")
    logger.info("  Num examples = %d", len(eval_dataset))
    logger.info("  Batch size = %d", args.eval_batch_size)
    model.eval()
    logits=[]   
    labels=[]
    concept_logits = []
    concept_labels = []
    representations = []
    indices = []
    for batch in tqdm(eval_dataloader,total=len(eval_dataloader)):
        inputs, label, concept_label, tok_to_line_map, indices_ = batch
        with torch.no_grad():
            output_ = model(inputs, tok_to_line_map=tok_to_line_map, return_representation=args.collect_representation)  
            logit = output_[0]
            # if args.train_concept:
            concept_logit = output_[1]
            if args.collect_representation:
                repr_ = output_[-1]
        
            if args.collect_representation:
                reprs, con_truth = accelerator.gather_for_metrics((repr_, concept_label))
                print(reprs.shape, con_truth.shape)
                reprs = reprs.view(-1, reprs.size(-1))
                con_truth = con_truth.view(-1,con_truth.size(-1))
                print(reprs.shape, con_truth.shape)
                mask = ~((con_truth == 0) | (con_truth == -1)).all(dim=-1)
                reprs = reprs[mask]
                con_truth = con_truth[mask]
                representations.append([reprs.detach().cpu().float().numpy(), con_truth.detach().cpu().float().numpy()])


        logit, label= accelerator.gather_for_metrics((logit, label))

        logits.append(logit.cpu().float().numpy())
        labels.append(label.cpu().float().numpy())
        
        # if args.train_concept:
        concept_logit, concept_label = accelerator.gather_for_metrics((concept_logit, concept_label))
        concept_logits.append(concept_logit.cpu().float().numpy())
        concept_labels.append(concept_label.cpu().float().numpy())

    logits=np.concatenate(logits,0)
    labels=np.concatenate(labels,0)
    

    # if args.model_type in set(['codegen', 'starcoder', 'codellama', 'qwen', 'deepseek', 'magicoder', 'codegemma']):
    preds=logits[:,1]>0.5
        # concept_preds = concept_logits[:,1] > 0.5
    # else:
    #     preds=logits[:,0]>0.5
        # concept_preds = concept_logits[:,0] > 0.5
    # os.makedirs(os.path.join(args.output_dir, args.project), exist_ok=True)
 
    test_acc, test_prec, test_recall, test_f1, test_tnr, test_fpr, test_fnr = calculate_metrics(labels, preds)
    # concept_eval_acc, concept_eval_prec, concept_eval_recall, concept_eval_f1, concept_eval_tnr, concept_eval_fpr, concept_eval_fnr = calculate_metrics(concept_labels, concept_preds)
    
    # if args.train_concept:
    concept_logits = np.concatenate(concept_logits, axis=0).reshape(-1, concept_logits[0].shape[-1])
    concept_labels = np.concatenate(concept_labels, axis=0).reshape(-1, concept_labels[0].shape[-1])
    # Step 2: Create mask for rows where not all elements are -1
    valid_mask = ~(concept_labels == -1).all(axis=1)
    # Step 3: Filter out invalid rows
    logits_valid = concept_logits[valid_mask]
    labels_valid = concept_labels[valid_mask]
    # Step 4: Binarize logits
    y_pred = (logits_valid > 0.5).astype(int)
    y_true = labels_valid.astype(int)
    # Step 5: Compute macro F1 score
    concept_eval_f1 = f1_score(y_true, y_pred, average="macro")
    accelerator.wait_for_everyone()
        
    if args.collect_representation:
        reprs = np.concatenate([x[0] for x in representations], 0)
        labs = np.concatenate([x[1] for x in representations], 0)
        print(reprs.shape, labs.shape)
        file_name = args.test_data_file.split(".")[-2].split("/")[-1]
        os.makedirs(args.representation_dir, exist_ok=True)
        import pickle
        with open(f'{args.representation_dir}/{file_name}.pkl', 'wb') as f:
            pickle.dump({"repr": reprs, "label": labs}, f)


    result = {
        "eval_acc": test_acc,
        "eval_prec": test_prec,
        "eval_recall": test_recall,
        "eval_f1": test_f1,
        "concept_eval_f1": concept_eval_f1,
    }
    # if args.train_concept:
    #     result["concept_eval_f1"] = concept_eval_f1
    return result 


def test_prob(args, model, tokenizer, collect_representation=False):
    eval_dataset = TextDataset(tokenizer, args,args.test_data_file)

    args.eval_batch_size = args.per_gpu_eval_batch_size * max(1, args.n_gpu)
    # Note that DistributedSampler samples randomly
    eval_sampler = SequentialSampler(eval_dataset) if args.local_rank == -1 else DistributedSampler(eval_dataset)
    eval_dataloader = DataLoader(eval_dataset, sampler=eval_sampler, batch_size=args.eval_batch_size)

    # multi-gpu evaluate
    if args.n_gpu > 1:
        model = torch.nn.DataParallel(model)

    # Eval!
    logger.info("***** Running Test *****")
    logger.info("  Num examples = %d", len(eval_dataset))
    logger.info("  Batch size = %d", args.eval_batch_size)
    eval_loss = 0.0
    nb_eval_steps = 0
    model.eval()
    logits=[]   
    labels=[]
    representations = []
    concept_logits = []
    concept_labels = []
    for batch in tqdm(eval_dataloader,total=len(eval_dataloader)):
        inputs = batch[0].to(args.device)        
        label=batch[1].to(args.device) 
        concept_label=batch[2].to(args.device) 
        with torch.no_grad():
            if collect_representation:
                output = model(inputs, return_representation=True)
                reprs.append(output[-1].cpu().float().numpy())
            else:
                output = model(inputs)
            logits.append(output[0].cpu().float().numpy())
            labels.append(label.cpu().float().numpy())
            # if args.train_concept:
            #     concept_logits.append(output[1].cpu().float().numpy())
            #     concept_labels.append(concept_label.cpu().float().numpy())
            if args.collect_representation:
                reprs, con_truth = accelerator.gather_for_metrics((repr_, concept_label))
                print(reprs.shape, con_truth.shape)
                reprs = reprs.view(-1, reprs.size(-1))
                con_truth = con_truth.view(-1,con_truth.size(-1))
                print(reprs.shape, con_truth.shape)
                mask = ~((con_truth == 0) | (con_truth == -1)).all(dim=-1)
                reprs = reprs[mask]
                con_truth = con_truth[mask]
                representations.append([reprs.detach().cpu().float().numpy(), con_truth.detach().cpu().float().numpy()])

    logits=np.concatenate(logits,0)
    labels=np.concatenate(labels,0)

    if collect_representation:
        reprs = np.concatenate(reprs, 0)
    # if args.model_type in set(['codegen', 'starcoder', 'codellama', 'qwen', 'deepseek', 'magicoder', 'codegemma']):
    preds=logits[:,1]>0.5
        # concept_preds = concept_logits[:,1] > 0.5
    # else:
    #     preds=logits[:,0]>0.5
        # concept_preds = concept_logits[:,0] > 0.5
 
    if args.collect_representation:
        reprs = np.concatenate([x[0] for x in representations], 0)
        labs = np.concatenate([x[1] for x in representations], 0)
        print(reprs.shape, labs.shape)
        file_name = args.test_data_file.split(".")[-2].split("/")[-1]
        os.makedirs(args.representation_dir, exist_ok=True)
        import pickle
        with open(f'{args.representation_dir}/{file_name}.pkl', 'wb') as f:
            pickle.dump({"repr": reprs, "label": labs}, f)

    test_acc, test_prec, test_recall, test_f1, test_tnr, test_fpr, test_fnr = calculate_metrics(labels, preds)
    concept_eval_f1 = 0
    # if args.train_concept:
    #     concept_logits=np.concatenate(concept_logits, 0)
    #     concept_labels=np.concatenate(concept_labels, 0)
    #     y_pred = (concept_logits > 0.5).astype(int)  
    #     y_true = concept_labels.astype(int)  # Ensure labels are in integer format
    #     concept_eval_f1 = f1_score(y_true, y_pred, average="micro")

    result = {
        "test_acc": test_acc,
        "test_prec": test_prec,
        "test_recall": test_recall,
        "test_f1": test_f1,
        "test_tnr": test_tnr,
        "test_tnr": test_tnr,
        "test_fnr": test_fnr,
        # "concept_eval_acc": concept_eval_acc,
        # "concept_eval_prec": concept_eval_prec,
        # "concept_eval_recall": concept_eval_recall,
        # "concept_eval_f1": concept_eval_f1,
        # "concept_eval_tnr": concept_eval_tnr,
        # "concept_eval_fpr": concept_eval_fpr,
        # "concept_eval_fnr": concept_eval_fnr,
    }
    return result

def load_model(path):
    index_file = os.path.join(path, "pytorch_model.bin.index.json")
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    weight_map = index_data["weight_map"]
    # 2. Collect all the shard filenames
    shard_files = sorted(list(set(weight_map.values())))
    full_state_dict = {}
    for i, shard_file in enumerate(shard_files):
        shard_path = os.path.join(path, shard_file)
        # Load shard (on CPU)
        print("Loading the shard ", shard_file)
        shard_state_dict = torch.load(shard_path)
        # Merge
        full_state_dict.update(shard_state_dict)
    return full_state_dict

                        
def main():
    parser = argparse.ArgumentParser()

    ## Required parameters
    parser.add_argument('--project', type=str, required=True, help="using dataset from this project.")
    parser.add_argument('--train_project', type=str, required=False, help="using training dataset from this project.")
    parser.add_argument('--model_dir', type=str, required=True, help="directory to store the model weights.")
    parser.add_argument("--train_data_file", default=None, type=str, required=True,
                        help="The input training data file (a text file).")
    parser.add_argument("--output_dir", default=None, type=str, required=True,
                        help="The output directory where the model predictions and checkpoints will be written.")
    parser.add_argument('--test_cwe', type=str, default=None, required=False, help="using dataset from this CWE for testing.")
    
    # run dir
    parser.add_argument('--run_dir', type=str, default="runs", help="parent directory to store run stats.")

    ## Other parameters
    parser.add_argument("--max_source_length", default=400, type=int,
                        help="The maximum total source sequence length after tokenization. Sequences longer than this will be truncated, sequences shorter will be padded.")
    parser.add_argument("--eval_data_file", default=None, type=str,
                        help="An optional input evaluation data file to evaluate the perplexity on (a text file).")
    parser.add_argument("--test_data_file", default=None, type=str,
                        help="An optional input evaluation data file to evaluate the perplexity on (a text file).")
                    
    parser.add_argument("--model_type", default="codegen", type=str,
                        help="The model architecture to be fine-tuned.")
    parser.add_argument("--model_name_or_path", default=None, type=str,
                        help="The model checkpoint for weights initialization.")

    parser.add_argument("--mlm", action='store_true',
                        help="Train with masked-language modeling loss instead of language modeling.")
    parser.add_argument("--mlm_probability", type=float, default=0.15,
                        help="Ratio of tokens to mask for masked language modeling loss")

    parser.add_argument("--config_name", default="", type=str,
                        help="Optional pretrained config name or path if not the same as model_name_or_path")
    parser.add_argument("--tokenizer_name", default="", type=str,
                        help="Optional pretrained tokenizer name or path if not the same as model_name_or_path")
    parser.add_argument("--cache_dir", default="", type=str,
                        help="Optional directory to store the pre-trained models downloaded from s3 (instread of the default one)")
    parser.add_argument("--block_size", default=-1, type=int,
                        help="Optional input sequence length after tokenization."
                             "The training dataset will be truncated in block of this size for training."
                             "Default to the model max input length for single sentence inputs (take into account special tokens).")
    parser.add_argument("--do_train", action='store_true',
                        help="Whether to run training.")
    parser.add_argument("--do_eval", action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--do_test", action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--do_test_prob", action='store_true',
                        help="Whether to run eval and save the prediciton probabilities.")    
    parser.add_argument("--do_test_with_accelerator", action='store_true',
                        help="Whether to test with accelerator and distributed checkpoints.") 
    parser.add_argument("--evaluate_during_training", action='store_true',
                        help="Run evaluation during training at each logging step.")
    parser.add_argument("--do_lower_case", action='store_true',
                        help="Set this flag if you are using an uncased model.")

    parser.add_argument("--weighted_sampler", action='store_true',
                        help="Whether to do project balanced sampler using WeightedRandomSampler.")
    # Soft F1 loss function
    parser.add_argument("--soft_f1", action='store_true',
                        help="Use soft f1 loss instead of regular cross entropy loss.")
    parser.add_argument("--class_weight", action='store_true',
                        help="Use class weight in the regular cross entropy loss.")
    # parser.add_argument("--vul_weight", default=1.0, type=float,
    #                     help="Weight for the vulnerable class in the regular cross entropy loss.")

    parser.add_argument("--train_batch_size", default=4, type=int,
                        help="Batch size per GPU/CPU for training.")
    parser.add_argument("--eval_batch_size", default=4, type=int,
                        help="Batch size per GPU/CPU for evaluation.")
    parser.add_argument('--gradient_accumulation_steps', type=int, default=1,
                        help="Number of updates steps to accumulate before performing a backward/update pass.")
    parser.add_argument("--learning_rate", default=5e-5, type=float,
                        help="The initial learning rate for Adam.")
    parser.add_argument("--weight_decay", default=0.0, type=float,
                        help="Weight deay if we apply some.")
    parser.add_argument("--adam_epsilon", default=1e-8, type=float,
                        help="Epsilon for Adam optimizer.")
    parser.add_argument("--max_grad_norm", default=1.0, type=float,
                        help="Max gradient norm.")
    parser.add_argument("--num_train_epochs", default=1.0, type=float,
                        help="Total number of training epochs to perform.")
    parser.add_argument("--max_steps", default=-1, type=int,
                        help="If > 0: set total number of training steps to perform. Override num_train_epochs.")
    parser.add_argument("--warmup_steps", default=0, type=int,
                        help="Linear warmup over warmup_steps.")
    parser.add_argument("--warmup_ratio", default=0.1, type=float,
                        help="Linear warmup ratio over all steps.")

    parser.add_argument('--logging_steps', type=int, default=1000,
                        help="Log every X updates steps.")
    parser.add_argument('--save_steps', type=int, default=50,
                        help="Save checkpoint every X updates steps.")
    parser.add_argument('--save_total_limit', type=int, default=None,
                        help='Limit the total amount of checkpoints, delete the older checkpoints in the output_dir, does not delete by default')
    parser.add_argument("--eval_all_checkpoints", action='store_true',
                        help="Evaluate all checkpoints starting with the same prefix as model_name_or_path ending and ending with step number")
    parser.add_argument("--no_cuda", action='store_true',
                        help="Avoid using CUDA when available")
    parser.add_argument('--overwrite_output_dir', action='store_true',
                        help="Overwrite the content of the output directory")
    parser.add_argument('--overwrite_cache', action='store_true',
                        help="Overwrite the cached training and evaluation sets")
    parser.add_argument('--seed', type=int, default=42,
                        help="random seed for initialization")
    parser.add_argument('--epoch', type=int, default=42,
                        help="random seed for initialization")
    parser.add_argument("--local_rank", type=int, default=-1,
                        help="For distributed training: local_rank")
    parser.add_argument('--max-patience', type=int, default=-1, help="Max iterations for model with no improvement.")
    parser.add_argument('--target_key', type=str, default="target", help="Target key for the classification.")
    parser.add_argument('--initial_task', type=str, default=None, help="Target key for the classification.")  
    parser.add_argument('--latest_task', type=str, default=None, help="Target key for the classification.")  
    parser.add_argument("--representation_dir", default=None, type=str, 
                        help="The output directory where the model representation will be written.")
    parser.add_argument("--collect_representation", action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--fine_tune_classifier_only", action='store_true',
                        help="Whether to fine_tune only the classifier.")
    parser.add_argument("--use_small_function_only", action='store_true',
                    help="Whether to fine_tune only the classifier.")
    parser.add_argument("--concepts", type=int, default=-1,
                    help="For distributed training: local_rank")
    parser.add_argument("--vul_weight", default=1.0, type=float,
                        help="Weight for vulnerability detection.")
    parser.add_argument("--concept_weight", default=0.25, type=float,
                        help="Weight for concept detection.")
    parser.add_argument("--loss_lr", action='store_true',
                    help="Whether to fine_tune only the classifier.")
    parser.add_argument("--train_concept", action='store_true',
                help="Whether to fine_tune only the classifier.")
    parser.add_argument("--clamp_features", action='store_true',
                    help="Whether to update loss dynamically")
    parser.add_argument("--clamp_factor", type=float, default=10,
                    help="For distributed training: local_rank")
    parser.add_argument("--clamp_k", type=int, default=10,
                    help="For distributed training: local_rank")
    parser.add_argument("--clamp_features_dir", default=None, type=str,
                        help="The output directory where the model representation will be written.")
    parser.add_argument("--max_statements", type=int, default=100,
                    help="maximum statements to consider")
                        
    args = parser.parse_args()


    accelerator = Accelerator(gradient_accumulation_steps=args.gradient_accumulation_steps)
    # accelerator = Accelerator() 
    print(accelerator.gradient_accumulation_steps)

    device = accelerator.device
    args.n_gpu = accelerator.num_processes
    args.device = device
    args.per_gpu_train_batch_size=args.train_batch_size 
    args.per_gpu_eval_batch_size=args.eval_batch_size // args.n_gpu
    # Setup logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO if args.local_rank in [-1, 0] else logging.WARN)
    logger.warning("device: %s, n_gpu: %s, distributed training: %s",
                   device, args.n_gpu, bool(args.n_gpu > 1))
    logger.info(accelerator.state, main_process_only=False)

    # Set seed
    set_seed(args.seed)

    args.start_epoch = 0
    args.start_step = 0
    checkpoint_last = os.path.join(args.output_dir, 'checkpoint-last')
    if os.path.exists(checkpoint_last) and os.listdir(checkpoint_last):
        args.model_name_or_path = os.path.join(checkpoint_last, 'model.bin')
        args.config_name = os.path.join(checkpoint_last, 'config.json')
        idx_file = os.path.join(checkpoint_last, 'idx_file.txt')
        with open(idx_file, encoding='utf-8') as idxf:
            args.start_epoch = int(idxf.readlines()[0].strip()) + 1

        step_file = os.path.join(checkpoint_last, 'step_file.txt')
        if os.path.exists(step_file):
            with open(step_file, encoding='utf-8') as stepf:
                args.start_step = int(stepf.readlines()[0].strip())

        logger.info("reload model from {}, resume from {} epoch".format(checkpoint_last, args.start_epoch))

    config_class, model_class, tokenizer_class = MODEL_CLASSES[args.model_type]
    config = config_class.from_pretrained(args.config_name if args.config_name else args.model_name_or_path,
                                          cache_dir=args.cache_dir if args.cache_dir else None)
    
    config.num_labels = 2
    if args.model_type not in ["codegen"]:
        tokenizer = tokenizer_class.from_pretrained(args.tokenizer_name,
                                                    do_lower_case=args.do_lower_case,
                                                    cache_dir=args.cache_dir if args.cache_dir else None)
    else:
        tokenizer = tokenizer_class.from_pretrained(args.tokenizer_name,
                                                    trust_remote_code=True)
    if args.block_size <= 0:
        args.block_size = tokenizer.max_len_single_sentence  # Our input block size will be the max possible for the model
    args.block_size = min(args.block_size, tokenizer.max_len_single_sentence)

    if args.model_name_or_path:
        # if args.model_type in ["starcoder", "codellama", "deepseek", "qwen", "deepseek"]:
        model = model_class.from_pretrained(args.model_name_or_path,
                                            use_cache = False,
                                            torch_dtype = torch.bfloat16,
                                            attn_implementation = "flash_attention_2")
            # if args.model_type == "qwen":
            #     model.gradient_checkpointing_enable()
        # else:
        #     model = model_class.from_pretrained(args.model_name_or_path,
        #                                         torch_dtype = torch.bfloat16,
        #                                     )
    else:
        model = model_class(config)
    
    tokenizer.pad_token = tokenizer.eos_token
    config.pad_token_id = tokenizer(tokenizer.pad_token, truncation=True, add_special_tokens=False)['input_ids'][0]
    print(config.pad_token_id, tokenizer.pad_token_id)
    # if args.model_type in ['codegen', 'starcoder', 'codellama', 'qwen', 'deepseek', 'magicoder', 'codegemma']:
        # if args.model_type in ['codellama']:
        # lora_config = LoraConfig(
        #     r=8,
        #     lora_alpha=32,
        #     lora_dropout=0.1,
        #     bias="none",
        #     target_modules=["q_proj", "v_proj", "o_proj", "gate_proj"],  # LLaMA’s attention layers
        #     task_type=TaskType.SEQ_CLS,  # or TaskType.CUSTOM if your forward pass is very custom
        # )
        # model = get_peft_model(model, lora_config)
    model = DecoderClassifier(model,config,tokenizer,args)
    model = model.to(dtype=torch.bfloat16)
    print(model)
    # else:
    #     model = Model(model,config,tokenizer,args)

    logger.info("Training/evaluation parameters %s", args)

    # Training
    if args.do_train:
        with accelerator.main_process_first():
            train_dataset = TextDataset(tokenizer, args, args.train_data_file)
            eval_dataset = TextDataset(tokenizer, args, args.eval_data_file)

        train(args, accelerator, train_dataset, eval_dataset, model, tokenizer)
    
    if args.clamp_features:
        imp_features_path = f"{args.clamp_features_dir}/important_features_top_{args.clamp_k}.json"
        with open(imp_features_path, "r") as f:
            impt_features = json.load(f)['features']
        args.clamp_vector = torch.ones(config.hidden_size, dtype=torch.float32)
        args.clamp_vector[impt_features] = args.clamp_factor
        # print(sum(y))
        args.clamp_vector = args.clamp_vector.to(device)
        args.clamp_vector = args.clamp_vector.unsqueeze(0).unsqueeze(0)
        args.clamp_vector = args.clamp_vector.to(torch.bfloat16)

    results = {}
    if args.do_eval and args.local_rank in [-1, 0]:
        checkpoint_prefix = f'checkpoint-best-f1/{args.project}/{args.model_dir}/merged_model'
        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))  
        model.load_state_dict(load_(output_dir))      
        model.to(args.device)
    
    if args.do_test_prob and args.local_rank in [-1, 0]:
        if args.collect_representation:
            assert args.representation_dir != None
        checkpoint_prefix = f'checkpoint-best-f1/{args.project}/{args.model_dir}/merged_model'
        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))  
        model.load_state_dict(load_model(output_dir), strict=True)

        if args.latest_task:
            checkpoint_prefix = f'checkpoint-best-f1/{args.latest_task}/{args.model_dir}/merged_model'
            output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))  
            model.load_state_dict(load_model(output_dir), strict=False)

        model = model.to(dtype=torch.bfloat16)       
        model = model.to(args.device)
        result = test_prob(args, model, tokenizer, collect_representation=args.collect_representation)
        logger.info("***** Test results *****")
        for key in sorted(result.keys()):
            logger.info("  %s = %s", key, str(round(result[key],4)))

    if args.do_test_with_accelerator and args.local_rank in [-1, 0]:
        eval_dataset = TextDataset(tokenizer, args, args.test_data_file)
        args.eval_batch_size = args.per_gpu_eval_batch_size * max(1, args.n_gpu)
        eval_dataloader = DataLoader(eval_dataset, shuffle=False, batch_size=args.eval_batch_size)

        no_decay = ['bias', 'LayerNorm.weight']
        optimizer_grouped_parameters = [
            {'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            'weight_decay': args.weight_decay},
            {'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)], 'weight_decay': 0.0}
        ]
        optimizer = AdamW(optimizer_grouped_parameters, lr=args.learning_rate, eps=args.adam_epsilon)
        # print(model.state_dict())
        eval_dataloader, model, optimizer = accelerator.prepare(eval_dataloader, model, optimizer)
        checkpoint_prefix = f'checkpoint-best-f1/{args.project}/{args.model_dir}'
        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))
        accelerator.load_state(output_dir, load_optimizer_states=False)

        result = test(args, accelerator, model, tokenizer)
        logger.info("***** Test results *****")
        for key in sorted(result.keys()):
            logger.info("  %s = %s", key, str(round(result[key],4)))
    
    return results


if __name__ == "__main__":
    main()
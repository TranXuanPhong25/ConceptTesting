import json
import gmpy2
import os
from collections import defaultdict
import argparse

def init_validate_outputs():
    _token_set = {"yes", "no", "true", "false"}
    
    PRECISION = gmpy2.mpfr(1e-12, 129)
    
    def validate_outputs(output1: str, output2: str) -> bool:
        def validate_lines(lines1, lines2):
            validate_line = lambda lines: lines[0].strip() == lines[1].strip()
            if len(lines1) != len(lines2):
                return False
            return all(map(validate_line, zip(lines1, lines2)))

        if validate_lines(output1.strip().split("\n"), output2.strip().split("\n")):
            return True

        tokens1, tokens2 = output1.strip().split(), output2.strip().split()
        if len(tokens1) != len(tokens2):
            return False

        for tok1, tok2 in zip(tokens1, tokens2):
            try:
                num1, num2 = gmpy2.mpfr(tok1, 129), gmpy2.mpfr(tok2, 129)
                if abs(num1 - num2) > PRECISION:
                    return False
            except ValueError:
                if tok1.lower() in _token_set:
                    tok1 = tok1.lower()
                if tok2.lower() in _token_set:
                    tok2 = tok2.lower()
                if tok1 != tok2:
                    return False

        return True

    return validate_outputs

validate_outputs = init_validate_outputs()

def process_task2(file_path):
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    with open(file_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            result[data['problem_id']][data['submission_id']][data['checked_submission_type']].append(data)
    test_result = defaultdict(lambda: defaultdict(str))
    for problem_id in result:
        for submission_id in result[problem_id]:
            outputs = []
            for data in result[problem_id][submission_id]["right_submission"]:
                if data['api_result']['result'] == 'success_run':
                    outputs.append(data['api_result']['output'])
            if len(outputs) == 1:
                test_result[problem_id][submission_id] = outputs[0]
            else:
                found_consistent = False
                for i in range(len(outputs)):
                    for j in range(i + 1, len(outputs)):
                        if validate_outputs(outputs[i], outputs[j]):
                            test_result[problem_id][submission_id] = outputs[i]
                            found_consistent = True
                            break
                    if found_consistent:
                        break
    return result, test_result

def exposure(result, test_result):
    exp = set()
    exp_total = 0
    for problem_id in result:
        for submission_id in result[problem_id]:
            for data in result[problem_id][submission_id]['wrong_submission']:
                exp_total += 1
                if test_result[problem_id][submission_id] != '':
                    id = data['checked_submission_id']
                    verdict = data['api_result']['result']
                    if verdict == 'success_run':
                        output = data['api_result']['output']
                        if not validate_outputs(output, test_result[problem_id][submission_id]):
                            exp.add((problem_id, id))
                    elif verdict == 'runtime_error' or verdict == 'time_limit_exceeded' or verdict == 'memory_limit_exceeded':
                        exp.add((problem_id, id))
    exp_value = len(exp)
    return exp_value, exp_total

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate Task 2 (Exposure) metrics")
    parser.add_argument("--model", type=str, required=True, help="Model name")
    args = parser.parse_args()

    all_results = {}

    model = args.model
    file_path = f'results/{model}/task2_exec.jsonl'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        exit()
    
    print(f"Processing {model} task2")
    result, test_result = process_task2(file_path)
    exp, exp_total = exposure(result, test_result)

    model_results = {
        'exp': exp,
        'exp_total': exp_total
    }
    
    model_results['exp_ratio'] = exp / exp_total if exp_total > 0 else 0
    
    all_results[model] = model_results

    print(f"{model} task2: {exp} / {exp_total} = {exp / exp_total * 100:.2f}%")

    output_file = 'stat/task2_exp_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_file}")

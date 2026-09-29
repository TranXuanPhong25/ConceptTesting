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

def process_task1(file_path):
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    with open(file_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            result[data['problem_id']][data['response_id']][data['checked_submission_type']].append(data)

    problem_ids = list(result.keys())
    test_result = defaultdict(lambda: defaultdict(str))
    for problem_id in result:
        for response_id in result[problem_id]:
            outputs = []
            for data in result[problem_id][response_id]["right_submission"]:
                if data['api_result']['result'] == 'success_run':
                    outputs.append(data['api_result']['output'])
            if len(outputs) == 1:
                test_result[problem_id][response_id] = outputs[0]
            else:
                found_consistent = False
                for i in range(len(outputs)):
                    for j in range(i + 1, len(outputs)):
                        if validate_outputs(outputs[i], outputs[j]):
                            test_result[problem_id][response_id] = outputs[i]
                            found_consistent = True
                            break
                    if found_consistent:
                        break
    return result, test_result, problem_ids

def cov_k(k, result, test_result):
    cov = set()
    cov_total = 0
    for problem_id in result:
        for response_id in result[problem_id]:
            if int(response_id) < k:
                for data in result[problem_id][response_id]['wrong_submission']:
                    cov_total += 1
                    if test_result[problem_id][response_id] != '':
                        id = data['checked_submission_id']
                        verdict = data['api_result']['result']
                        if verdict == 'success_run':
                            output = data['api_result']['output']
                            if not validate_outputs(output, test_result[problem_id][response_id]):
                                cov.add((problem_id, id))
                        elif verdict == 'runtime_error' or verdict == 'time_limit_exceeded' or verdict == 'memory_limit_exceeded':
                            cov.add((problem_id, id))
    cov_value = len(cov)
    return cov_value, cov_total

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate Task 1 (Coverage) metrics")
    parser.add_argument("--model", type=str, required=True, help="Model name")
    args = parser.parse_args()

    all_results = {}
    all_problem_ids = {}

    model = args.model
    file_path = f'results/{model}/task1_exec.jsonl'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        exit()
    
    print(f"Processing {model} task1")
    result, test_result, problem_ids = process_task1(file_path)
    all_problem_ids[model] = problem_ids
    print(f"{model} contains {len(problem_ids)} problem_ids")

    if len(result) == 0:
        print(f"No data for {model} task1")
        exit()
    cov_1, cov_total_1 = cov_k(1, result, test_result)
    cov_5, cov_total_5 = cov_k(5, result, test_result)
    cov_10, cov_total_10 = cov_k(10, result, test_result)
    cov_20, cov_total_20 = cov_k(20, result, test_result)

    model_results = {
        'cov_1': cov_1,
        'cov_5': cov_5,
        'cov_10': cov_10,
        'cov_20': cov_20,
        'cov_total_1': cov_total_1,
        'cov_total_5': cov_total_5,
        'cov_total_10': cov_total_10,
        'cov_total_20': cov_total_20
    }
    
    model_results['cov_1_ratio'] = cov_1 / cov_total_1 if cov_total_1 > 0 else 0.0
    model_results['cov_5_ratio'] = cov_5 / cov_total_1 if cov_total_1 > 0 else 0.0
    model_results['cov_10_ratio'] = cov_10 / cov_total_1 if cov_total_1 > 0 else 0.0
    model_results['cov_20_ratio'] = cov_20 / cov_total_1 if cov_total_1 > 0 else 0.0
    
    all_results[model] = model_results

    print(f"{model} task1: {cov_1}, {cov_5}, {cov_10}, {cov_20}")
    print(f"{model} task1: {cov_total_1}, {cov_total_5}, {cov_total_10}, {cov_total_20}")
    print(f"{model} task1: {cov_1 / cov_total_1 * 100:.2f}%, {cov_5 / cov_total_1 * 100:.2f}%, {cov_10 / cov_total_1 * 100:.2f}%, {cov_20 / cov_total_1 * 100:.2f}%")

    output_file = 'stat/task1_cov_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_file}")

    problem_ids_file = 'stat/all_model_problem_ids.json'
    with open(problem_ids_file, 'w', encoding='utf-8') as f:
        json.dump(all_problem_ids, f, indent=2, ensure_ascii=False)
    
    print(f"Problem IDs saved to {problem_ids_file}")

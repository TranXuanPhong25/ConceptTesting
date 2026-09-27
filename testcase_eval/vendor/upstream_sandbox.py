import os
import re
import tempfile
import subprocess
import time
import random
import string
import json
import resource
import multiprocessing as mp
import threading
import argparse
import psutil
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from collections import defaultdict
from datasets import load_dataset

class ExecutionResult(Enum):
    SUCCESS_RUN = "success_run"
    PASSED = "passed"
    COMPILATION_ERROR = "compilation_error"
    WRONG_ANSWER = "wrong_answer"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    SYSTEM_ERROR = "system_error"
    INVALID_INPUT = "invalid_input"


class LanguageConfig:
    def __init__(self, name: str, compile_cmd: Optional[str] = None, 
                 compile_flags: str = "", execute_cmd: str = "", 
                 execute_flags: str = "", file_ext: str = "",
                 is_compiled: bool = False, timeout_factor: float = 1.0):
        self.name = name
        self.compile_cmd = compile_cmd
        self.compile_flags = compile_flags
        self.execute_cmd = execute_cmd
        self.execute_flags = execute_flags
        self.file_ext = file_ext
        self.is_compiled = is_compiled
        self.timeout_factor = timeout_factor


class MultiLanguageExecutor:
    
    def __init__(self):
        self.languages = self._init_languages()
    
    def _init_languages(self) -> Dict[str, LanguageConfig]:
        return {
            "Python 2": LanguageConfig(
                name="Python 2",
                compile_cmd="python2",
                compile_flags="-m py_compile",
                execute_cmd="python2",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "Python 3": LanguageConfig(
                name="Python 3", 
                compile_cmd="python3",
                compile_flags="-m py_compile",
                execute_cmd="python3",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 2": LanguageConfig(
                name="PyPy 2",
                compile_cmd="pypy2",
                compile_flags="-m py_compile",
                execute_cmd="pypy2",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 3": LanguageConfig(
                name="PyPy 3",
                compile_cmd="pypy3", 
                compile_flags="-m py_compile",
                execute_cmd="pypy3",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 3-64": LanguageConfig(
                name="PyPy 3-64",
                compile_cmd="pypy3",
                compile_flags="-m py_compile",
                execute_cmd="pypy3",
                execute_flags="-u",
                file_ext=".py", 
                is_compiled=False,
                timeout_factor=2.0
            ),
  
            "C++14 (GCC 6-32)": LanguageConfig(
                name="C++14 (GCC 6-32)",
                compile_cmd="g++",
                compile_flags="-std=c++14 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++17 (GCC 7-32)": LanguageConfig(
                name="C++17 (GCC 7-32)",
                compile_cmd="g++",
                compile_flags="-std=c++17 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++20 (GCC 13-64)": LanguageConfig(
                name="C++20 (GCC 13-64)",
                compile_cmd="g++",
                compile_flags="-std=c++20 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++23 (GCC 14-64, winlibs)": LanguageConfig(
                name="C++23 (GCC 14-64, winlibs)",
                compile_cmd="g++",
                compile_flags="-std=c++23 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++23 (GCC 14-64, msys2)": LanguageConfig(
                name="C++23 (GCC 14-64, msys2)",
                compile_cmd="g++",
                compile_flags="-std=c++23 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),

            "Java 8": LanguageConfig(
                name="Java 8",
                compile_cmd="javac",
                compile_flags="",
                execute_cmd="java",
                execute_flags="-XX:+UseSerialGC -XX:TieredStopAtLevel=1 -XX:NewRatio=5 -Xms8M -Xss64M -DONLINE_JUDGE=true",
                file_ext=".java",
                is_compiled=True,
                timeout_factor=1.5
            ),
            "Java 21": LanguageConfig(
                name="Java 21",
                compile_cmd="javac",
                compile_flags="",
                execute_cmd="java", 
                execute_flags="-XX:+UseSerialGC -XX:TieredStopAtLevel=1 -XX:NewRatio=5 -Xms8M -Xss64M -DONLINE_JUDGE=true",
                file_ext=".java",
                is_compiled=True,
                timeout_factor=1.5
            )
        }
    
    def _random_class_name(self, prefix: str = "Tmp") -> str:
        return prefix + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    def _replace_java_class_name(self, java_code: str, new_class_name: str) -> str:
        main_class_pattern = r'public\s+class\s+(\w+).*?public\s+static\s+void\s+main'
        main_match = re.search(main_class_pattern, java_code, re.DOTALL)
        
        if main_match:
            original_class_name = main_match.group(1)
            java_code = re.sub(f'public\\s+class\\s+{re.escape(original_class_name)}', 
                             f'public class {new_class_name}', java_code)
            java_code = re.sub(f'\\b{re.escape(original_class_name)}\\s*\\(', 
                             f'{new_class_name}(', java_code)
        else:
            java_code = re.sub(r'public\s+class\s+(\w+)', f'public class {new_class_name}', java_code)
            java_code = re.sub(r'(?<!public\s)(?<!public\s\s)(?<!public\s\s\s)(?<!public\s\s\s\s)class\s+(\w+)', 
                              f'class {new_class_name}', java_code, count=1)
        
        return java_code
    
    def execute(self, language: str, code: str, input_data: str = "", 
                time_limit: float = 3.0, memory_limit: int = 512) -> Dict[str, Any]:

        if language not in self.languages:
            return {
                "result": ExecutionResult.COMPILATION_ERROR.value,
                "output": "",
                "error": f"Unsupported language: {language}",
                "time": 0.0,
                "memory": 0
            }
        
        lang_config = self.languages[language]
        actual_timeout = time_limit * lang_config.timeout_factor
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                
                if language.startswith("Java"):
                    class_name = self._random_class_name()
                    code = self._replace_java_class_name(code, class_name)
                    source_file = tmpdir_path / f"{class_name}{lang_config.file_ext}"
                else:
                    source_file = tmpdir_path / f"main{lang_config.file_ext}"
                
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                if lang_config.is_compiled and lang_config.compile_cmd:
                    if language.startswith("Java"):
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file)]
                    elif language.startswith("C++"):
                        executable = tmpdir_path / "main"
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file), "-o", str(executable)]
                    elif language.startswith("Python") or language.startswith("PyPy"):
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file)]
                    
                    try:
                        compile_result = subprocess.run(
                            compile_cmd,
                            cwd=tmpdir,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if compile_result.returncode != 0:
                            return {
                                "result": ExecutionResult.COMPILATION_ERROR.value,
                                "output": "",
                                "error": compile_result.stderr,
                                "time": 0.0,
                                "memory": 0
                            }
                    except subprocess.TimeoutExpired:
                        return {
                            "result": ExecutionResult.COMPILATION_ERROR.value,
                            "output": "",
                            "error": "Compilation timeout",
                            "time": 0.0,
                            "memory": 0
                        }
                
                if language.startswith("Java"):
                    java_flags = lang_config.execute_flags.split()
                    java_flags.append(f"-Xmx{memory_limit}M")
                    execute_cmd = [lang_config.execute_cmd] + java_flags + [class_name]
                elif language.startswith("C++"):
                    execute_cmd = [str(executable)]
                elif language.startswith("Python") or language.startswith("PyPy"):
                    execute_cmd = [lang_config.execute_cmd] + lang_config.execute_flags.split() + [str(source_file)]

                try:
                    def preexec_fn():
                        if not language.startswith("Java") and memory_limit > 0:
                            memory_limit_bytes = memory_limit * 1024 * 1024
                            resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))

                    process = subprocess.Popen(
                        execute_cmd,
                        cwd=tmpdir,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        preexec_fn=preexec_fn if os.name == 'posix' else None
                    )

                    try:
                        processed_input = input_data
                        if processed_input and not processed_input.endswith('\n'):
                            processed_input += '\n'
                        
                        start_time = time.time()
                        
                        max_memory = 0
                        stop_monitoring = threading.Event()
                        
                        def monitor_memory():
                            nonlocal max_memory
                            try:
                                p = psutil.Process(process.pid)
                                while not stop_monitoring.is_set() and p.is_running():
                                    try:
                                        memory_info = p.memory_info()
                                        current_memory = memory_info.rss // 1024
                                        max_memory = max(max_memory, current_memory)
                                        time.sleep(0.01)
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        break
                            except Exception:
                                pass
                        
                        monitor_thread = threading.Thread(target=monitor_memory, daemon=False)
                        monitor_thread.start()
                        
                        try:
                            stdout, stderr = process.communicate(input=processed_input, timeout=actual_timeout)
                            execution_time = time.time() - start_time
                        finally:
                            stop_monitoring.set()
                            monitor_thread.join(timeout=1.0)
                        
                    except subprocess.TimeoutExpired:
                        process.kill()
                        execution_time = actual_timeout
                        return {
                            "result": ExecutionResult.TIME_LIMIT_EXCEEDED.value,
                            "output": "",
                            "error": "Execution timeout",
                            "time": execution_time,
                            "memory": 0
                        }

                    if process.returncode != 0:
                        if process.returncode in (-9, 137):
                            return {
                                "result": ExecutionResult.MEMORY_LIMIT_EXCEEDED.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory
                            }
                        elif (stderr and any(keyword in stderr.lower() for keyword in 
                                            ['bad_alloc', 'out of memory', 'memory allocation', 'cannot allocate'])) or \
                            (max_memory > memory_limit * 1024 * 0.9):
                            return {
                                "result": ExecutionResult.MEMORY_LIMIT_EXCEEDED.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory
                            }
                        else:
                            return {
                                "result": ExecutionResult.RUNTIME_ERROR.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory
                            }

                    return {
                        "result": ExecutionResult.SUCCESS_RUN.value,
                        "output": stdout,
                        "error": stderr,
                        "time": execution_time,
                        "memory": max_memory
                    }
                    
                except Exception as e:
                    return {
                        "result": ExecutionResult.RUNTIME_ERROR.value,
                        "output": "",
                        "error": str(e),
                        "time": 0.0,
                        "memory": 0
                    }
        
        except Exception as e:
            return {
                "result": ExecutionResult.SYSTEM_ERROR.value,
                "output": "",
                "error": f"System error: {str(e)}",
                "time": 0.0,
                "memory": 0
            }


def execute_single_task(task_data):
    model_name, task_type, problem_id, submission_id, response_id, input, checked_submission_id, checked_submission_type, checked_submission_verdict, checked_submission_language, checked_submission_code = task_data

    if input.strip() == "ERROR" or input.strip() == "":
        api_call_record = {
            "model_name": model_name,
            "task_type": task_type,
            "problem_id": problem_id,
            "submission_id": submission_id,
            "response_id": response_id,
            "input": input,
            "checked_submission_id": checked_submission_id,
            "checked_submission_type": checked_submission_type,
            "checked_submission_verdict": checked_submission_verdict,
            "checked_submission_language": checked_submission_language,
            "api_result": {
                "result": ExecutionResult.INVALID_INPUT.value,
                "output": "",
                "error": "INVALID_INPUT",
                "time": 0.0,
                "memory": 0
            },
            "timestamp": time.time()
        }
        return api_call_record, None



    executor = MultiLanguageExecutor()
    
    api_params = {
        "language": checked_submission_language,
        "code": checked_submission_code,
        "input_data": input,
        "time_limit": 3.0,
        "memory_limit": 512
    }
    
    try:
        result = executor.execute(**api_params)

        api_call_record = {
            "model_name": model_name,
            "task_type": task_type,
            "problem_id": problem_id,
            "submission_id": submission_id,
            "response_id": response_id,
            "input": input,
            "checked_submission_id": checked_submission_id,
            "checked_submission_type": checked_submission_type,
            "checked_submission_verdict": checked_submission_verdict,
            "checked_submission_language": checked_submission_language,
            "api_result": result,
            "timestamp": time.time()
        }
        
        return api_call_record, None
        
    except Exception as e:
        api_call_record = {
            "model_name": model_name,
            "task_type": task_type,
            "problem_id": problem_id,
            "submission_id": submission_id,
            "response_id": response_id,
            "input": input,
            "checked_submission_id": checked_submission_id,
            "checked_submission_type": checked_submission_type,
            "checked_submission_verdict": checked_submission_verdict,
            "checked_submission_language": checked_submission_language,
            "api_result": {
                "result": ExecutionResult.SYSTEM_ERROR.value,
                "output": "",
                "error": f"System error: {str(e)}",
                "time": 0.0,
                "memory": 0
            },
            "timestamp": time.time()
        }
        return api_call_record, str(e)

def save_result_to_jsonl(result, output_file):
    with open(output_file, 'a', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
        f.write('\n')

def load_existing_results(output_file):
    completed_task_keys = set()
    
    if not os.path.exists(output_file):
        return completed_task_keys
    
    print(f"Reading existing results file: {output_file}")
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())

                    model_name = data.get('model_name')
                    task_type = data.get('task_type')
                    problem_id = data.get('problem_id')
                    submission_id = str(data.get('submission_id'))
                    response_id = str(data.get('response_id'))
                    checked_submission_id = str(data.get('checked_submission_id'))
                    
                    task_key = (model_name, task_type, problem_id, submission_id, response_id, checked_submission_id)
                    
                    completed_task_keys.add(task_key)
                        
                except json.JSONDecodeError as e:
                    print(f"Warning: Line {line_num} JSON parsing failed: {e}")
                    continue
                    
    except Exception as e:
        print(f"Error reading results file: {e}")
        return completed_task_keys
    
    print(f"Loaded {len(completed_task_keys)} completed tasks")
    return completed_task_keys

def main(model_name, task_id):
    num_workers = 64
    print(f"Detected {num_workers} CPU cores, using {num_workers} concurrent processes")
    
    output_file = f"results/{model_name}/task{task_id}_exec.jsonl"
    completed_task_keys = load_existing_results(output_file)

    all_tasks = []
    filtered_tasks = []
    
    test_file = f"results/{model_name}/task{task_id}_ext.jsonl"
    if task_id == 1:
        dataset_submission_all = load_dataset("TestCase-Eval/submission_all", split="train")
        submission_dict = defaultdict(list)
        for submission in dataset_submission_all:
            submission_dict[submission["problem_id"]].append(submission)
        
        with open(test_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() == "":
                    continue
                data = json.loads(line.strip())
                task_type = data["extra_info"]["task_type"]
                problem_id = data["extra_info"]["problem_id"]
                submission_id = str(data["extra_info"].get("submission_id", ""))
                response_id = str(data["extra_info"]["response_id"])
                input = data["test"]

                for submission in submission_dict[problem_id]:
                    checked_submission_id = str(submission["id"])
                    checked_submission_type = submission["type"]
                    checked_submission_verdict = submission["verdict"]
                    checked_submission_language = submission["language"]
                    checked_submission_code = submission["source"]

                    task_key = (model_name, task_type, problem_id, submission_id, response_id, checked_submission_id)
                    all_tasks.append(task_key)

                    if task_key in completed_task_keys:
                        continue

                    task = (model_name, task_type, problem_id, submission_id, response_id, input, checked_submission_id, checked_submission_type, checked_submission_verdict, checked_submission_language, checked_submission_code)
                    filtered_tasks.append(task)
    else:
        dataset_submission_lite = load_dataset("TestCase-Eval/submission_lite", split="train")
        submission_dict = defaultdict(list)
        for submission in dataset_submission_lite:
            submission_dict[submission["problem_id"]].append(submission)
        
        with open(test_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() == "":
                    continue
                data = json.loads(line.strip())
                task_type = data["extra_info"]["task_type"]
                problem_id = data["extra_info"]["problem_id"]
                submission_id = str(data["extra_info"].get("submission_id", ""))
                response_id = str(data["extra_info"]["response_id"])
                input = data["test"]

                for submission in submission_dict[problem_id]:
                    checked_submission_id = str(submission["id"])
                    checked_submission_type = submission["type"]
                    checked_submission_verdict = submission["verdict"]
                    checked_submission_language = submission["language"]
                    checked_submission_code = submission["source"]

                    if checked_submission_type == "wrong_submission" and checked_submission_id != submission_id:
                        continue

                    task_key = (model_name, task_type, problem_id, submission_id, response_id, checked_submission_id)
                    all_tasks.append(task_key)

                    if task_key in completed_task_keys:
                        continue

                    task = (model_name, task_type, problem_id, submission_id, response_id, input, checked_submission_id, checked_submission_type, checked_submission_verdict, checked_submission_language, checked_submission_code)
                    filtered_tasks.append(task)

    print(f"Total tasks: {len(all_tasks)}")
    print(f"Completed tasks: {len(completed_task_keys)}")
    print(f"Tasks to execute: {len(filtered_tasks)}")

    if not filtered_tasks:
        print("All tasks are completed, no new tasks to execute")
        return

    tasks = filtered_tasks

    completed_tasks = 0
    success_count = 0
    start_time = time.time()
    
    file_lock = threading.Lock()
    
    def result_callback(result_with_error):
        nonlocal completed_tasks, success_count
        
        result, error = result_with_error
        
        with file_lock:
            save_result_to_jsonl(result, output_file)
        
        completed_tasks += 1
        
        if result['api_result'].get('result') == ExecutionResult.SUCCESS_RUN.value:
            success_count += 1
        
        if completed_tasks % 100 == 0 or completed_tasks == len(tasks):
            elapsed_time = time.time() - start_time
            tasks_per_second = completed_tasks / elapsed_time if elapsed_time > 0 else 0
            remaining_tasks = len(tasks) - completed_tasks
            eta_seconds = remaining_tasks / tasks_per_second if tasks_per_second > 0 else 0
            
            print(f"Runtime: {elapsed_time/3600:.2f}h | Progress: {completed_tasks}/{len(tasks)} "
                  f"({completed_tasks/len(tasks)*100:.1f}%) "
                  f"Success: {success_count}/{completed_tasks} ({success_count/completed_tasks*100:.1f}%) "
                  f"Speed: {tasks_per_second:.1f} tasks/s "
                  f"ETA: {eta_seconds:.0f}s {eta_seconds/60:.1f}m {eta_seconds/3600:.1f}h")
        
        if error:
            print(f"Task {result['model_name']} {result['task_type']} {result['problem_id']} {result['submission_id']} {result['response_id']} {result['checked_submission_id']} failed: {error}")
    
    def error_callback(error):
        print(f"Process execution error: {error}")
    
    print("Starting multi-process execution...")
    
    with mp.Pool(processes=num_workers) as pool:
        for task in tasks:
            pool.apply_async(
                execute_single_task, 
                args=(task,),
                callback=result_callback,
                error_callback=error_callback
            )
        
        pool.close()
        pool.join()
    
    total_time = time.time() - start_time
    total_all_tasks = len(all_tasks)
    
    print("\nAll tests completed!")
    print(f"Execution time: {total_time:.2f}s")
    print(f"Number of tasks executed: {len(tasks)}")
    print(f"Total tasks: {total_all_tasks}")
    print(f"Success: {success_count}/{completed_tasks} ({success_count/completed_tasks*100:.1f}%)")
    if len(tasks) > 0:
        print(f"Average speed: {len(tasks)/total_time:.1f} tasks/s")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multi-language program execution sandbox')
    parser.add_argument("--model", type=str, required=True, help="Model name")
    parser.add_argument('--task', type=int, choices=[1, 2], default=None, 
                       help='Task ID (1 or 2) to run, if not specified, run all tasks')
    
    args = parser.parse_args()
    
    if args.task is not None:
        task_list = [args.task]
    else:
        task_list = [1, 2]
    
    print(f"Running model: {args.model}")
    print(f"Running tasks: {task_list}")
    
    for task_id in task_list:
        main(args.model, task_id)

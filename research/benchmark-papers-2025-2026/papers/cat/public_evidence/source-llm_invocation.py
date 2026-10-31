import re
import os
import time
import random
import requests
import litellm
import json
from lance_logger import LanceLogger
import subprocess
from constants_config import MAX_TOKENS_NUM
        

class LLMInvocation:
    def __init__(self, model: str):
        self.model = model
        self.logger = LanceLogger.initialize_logger(__name__)

    def trim_prompt_java_initializations(self, prompt_content: str) -> str:
        lines = prompt_content.split('\n')
        result_lines = []
        in_all_initializations = False
        skip_until_empty = False
        
        for line in lines:
            if '## All Initializations' in line:
                in_all_initializations = True
                result_lines.append(line)
                continue
            
            if in_all_initializations:
                if line.strip().startswith('java.'):
                    skip_until_empty = True
                    continue
                
                if skip_until_empty:
                    if not line.strip():
                        skip_until_empty = False
                        result_lines.append(line)
                    continue
            
            result_lines.append(line)
        
        trimmed = '\n'.join(result_lines)
        return trimmed

    def trim_prompt_for_fixing(self, prompt_content: str) -> str:
        lines = prompt_content.split('\n')
        result_lines = []
        in_source_file_section = False
        
        for line in lines:
            if line.strip().startswith('## Source File'):
                in_source_file_section = True
                result_lines.append(line)
                result_lines.append("(Content trimmed to reduce prompt size)")
                result_lines.append("")
                continue
            
            if line.strip().startswith('## Failed Tests'):
                in_source_file_section = False
                result_lines.append(line)
                continue
            
            if in_source_file_section:
                continue
            result_lines.append(line)
        trimmed = '\n'.join(result_lines)
        return trimmed

    def is_complete_java_test_function(self,code: str) -> bool:
        if not code or not code.strip():
            return False

        method_sig = re.search(
            r"\b(public|protected)?\s*void\s+\w+\s*\(",
            code
        )
        if not method_sig:
            return False

        if "{" not in code or "}" not in code:
            return False

        if code.count("{") != code.count("}"):
            return False

        last_close = code.rfind("}")
        if last_close < len(code.strip()) - 2:
            tail = code[last_close + 1:].strip()
            if tail:
                return False
        body_match = re.search(
            r"\{([\s\S]*)\}",
            code
        )
        if not body_match:
            return False

        body = body_match.group(1)

        body_wo_comments = re.sub(r"//.*|/\*[\s\S]*?\*/", "", body).strip()

        if ";" not in body_wo_comments:
            return False

        return True

    def truncate_incomplete_test(self, output_str: str) -> str:
        if "new_tests:" not in output_str:
            return ""

        cleaned_output = re.sub(r'```yaml\s*', '', output_str)
        cleaned_output = re.sub(r'```\s*', '', cleaned_output)
        
        parts = cleaned_output.split("new_tests:")
        if len(parts) > 1:
            body = "\n".join(parts[1:])
        else:
            body = parts[0] if parts else ""

        blocks = re.split(
            r"(?=^\s*-\s*test_behavior:\s*\|)",
            body,
            flags=re.MULTILINE
        )

        valid_blocks = []
        total_blocks = 0
        skipped_no_test_code = 0
        skipped_no_code_match = 0
        skipped_incomplete_function = 0
        skipped_no_void = 0

        for block in blocks:
            if not block.strip():
                continue

            total_blocks += 1

            if "test_code:" not in block:
                skipped_no_test_code += 1
                continue

            m = re.search(
                r"test_code:\s*\|\s*\n(?P<code>[\s\S]*?)(?=\n\s*new_imports_code:|\n\s*-\s*test_behavior:|\Z)",
                block,
                re.MULTILINE
            )
            
            if not m:
                skipped_no_code_match += 1
                continue

            code = m.group("code")
            
            if not code or not code.strip():
                skipped_no_code_match += 1
                continue
            

            if not self.is_complete_java_test_function(code):
                skipped_incomplete_function += 1
                continue

            if not re.search(r"\bvoid\s+\w+\s*\(", code):
                skipped_no_void += 1
                continue

            valid_blocks.append(block.rstrip())

        self.logger.info(f"[DEBUG] truncate_incomplete_test summary: "
                        f"total={total_blocks}, valid={len(valid_blocks)}, "
                        f"no_test_code={skipped_no_test_code}, no_code_match={skipped_no_code_match}, "
                        f"incomplete_func={skipped_incomplete_function}, no_void={skipped_no_void}")

        if not valid_blocks:
            return "new_tests:\n"

        return "new_tests:\n" + "\n".join(valid_blocks) + "\n"

    def generate_with_iter_content(self, OLLAMA_API_URL, completion_params, max_time=30):
        completion_params = dict(completion_params)

        collected_chunks = []  # Use list instead of string concatenation
        start_time = time.time()
        print_buffer = []  # Buffer for batched printing
        last_print_time = start_time
        line_count = 0
        empty_line_count = 0
        non_data_line_count = 0

        headers = {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": "Bearer <redacted>"
        }

        try:
            with requests.post(
                OLLAMA_API_URL,
                headers=headers,
                json=completion_params,
                stream=True,
                timeout=None
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    line_count += 1
                    current_time = time.time()
                    if current_time - start_time > max_time:
                        break

                    if not line:
                        empty_line_count += 1
                        continue

                    line = line.strip()
                    if not line.startswith("data: "):
                        non_data_line_count += 1
                        continue

                    data = line[6:]  
                    if data == "[DONE]":
                        break

                    try:
                        chunk_json = json.loads(data)
                        if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                            delta = chunk_json["choices"][0].get("delta", {}).get("content")
                            if delta:
                                collected_chunks.append(delta)
                                print_buffer.append(delta)
                                if current_time - last_print_time > 0.1:
                                    print("".join(print_buffer), end="", flush=True)
                                    print_buffer.clear()
                                    last_print_time = current_time
                            else:
                                finish_reason = chunk_json["choices"][0].get("finish_reason")
                                if finish_reason:
                                    break
                        elif "error" in chunk_json:
                            error_msg = chunk_json['error']
                            if isinstance(error_msg, dict):
                                error_text = error_msg.get('message', '')
                            else:
                                error_text = str(error_msg)
                            if 'context length' in error_text.lower() or 'tokens to keep' in error_text.lower():
                                return "__PROMPT_TOO_LONG__", -1, -1
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"[DEBUG] JSON parse error: {e}, line: {data[:200]}")

                if print_buffer:
                    print("".join(print_buffer), end="", flush=True)

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"[DEBUG] HTTP Error: {e}, Response: {e.response.text if e.response else 'N/A'}")
            return "", -1, -1
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"[DEBUG] Connection Error: {e}")
            return "", -1, -1
        except Exception as e:
            self.logger.error(f"[DEBUG] Exception during streaming request: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return "", -1, -1

        raw_collected_text = "".join(collected_chunks)

        if not raw_collected_text:
            return "", -1, -1

        collected_text = self.truncate_incomplete_test(raw_collected_text)

        if not collected_text or collected_text == "new_tests:\n":
            self.logger.warning(f"[DEBUG] truncate_incomplete_test returned empty or minimal result")
            self.logger.warning(f"[DEBUG] Raw text had 'new_tests:': {'new_tests:' in raw_collected_text}")
            self.logger.warning(f"[DEBUG] Raw text length: {len(raw_collected_text)}, truncated length: {len(collected_text)}")

        prompt_tokens = -1
        completion_tokens = -1

        return collected_text, prompt_tokens, completion_tokens

    def call_model(self, prompt: dict, max_tokens=MAX_TOKENS_NUM, temperature=0.2):
        if "system" not in prompt or "user" not in prompt:
            raise KeyError("The prompt dictionary must contain 'system' and 'user' keys.")

        if prompt["system"] == "":
            messages = [{"role": "user", "content": prompt["user"]}]
        else:
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ]

        if self.model == "deepseek-r1":
            completion_params = {
                "model": "sagemaker/endpoint-deepseek-r1-nashid",
                "messages": [{"role": "user", "content": "Are you better than GPT-4o for test generation and why?"}],
                "max_tokens": max_tokens,
                "stream": True,
                "temperature": temperature,
                "aws_region_name": "us-east-2"
            }
        else:
            completion_params = {
                "model": "qwen3-coder:30b",
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": True,
                "temperature": temperature,
            }

        OLLAMA_API_URL = "http://localhost:11434/v1/chat/completions"
        os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
        os.environ["OPENAI_API_KEY"] = "ollama"

        max_retries = 3
        base_delay = 2  # base delay in seconds

        for attempt in range(max_retries):
            try:
                self.logger.info(f"LLM starts generating...attemp: {attempt}")
                dytimeout = 300  # increase timeout with each attempt
                model_response_str,prompt_token,return_token = self.generate_with_iter_content(OLLAMA_API_URL, completion_params, max_time=dytimeout)
                
                if model_response_str == "__PROMPT_TOO_LONG__":
                    self.logger.warning("Prompt too long, trimming and retrying...")
                    for msg in completion_params["messages"]:
                        if msg["role"] == "user":
                            if "correct the code according to the compilation errors" in msg["content"]:
                                msg["content"] = self.trim_prompt_for_fixing(msg["content"])
                            else:
                                msg["content"] = self.trim_prompt_java_initializations(msg["content"])
                            break
                    continue
                
                is_invalid = False
                if "new_tests" not in model_response_str:
                    is_invalid = True
                elif model_response_str.strip() == "new_tests:":
                    is_invalid = True
                elif "test_code:" not in model_response_str:
                    is_invalid = True
                elif not re.search(r"test_code:\s*\|\s*\n\s+\S", model_response_str):
                    is_invalid = True
                
                if is_invalid:
                    self.logger.info(f"Response is invalid (empty or no tests). Retrying...\n Invalid Output: {model_response_str}")
                    for msg in completion_params["messages"]:
                        if msg["role"] == "user":
                            msg["content"] += "\n\nNote: Just tried once, you generated too lengthy code which got truncated. Please generate shorter, more concise test code this time."
                            break
                    continue
                return (
                    model_response_str,
                    prompt_token,
                    return_token
                )
            except requests.exceptions.Timeout:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                self.logger.warning(
                    f"Timeout: LLM took too long to respond. Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)
                continue
            except Exception as e:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limit exceeded. exception: {e}"
                      f"Retrying in {delay:.2f} seconds... "
                      f"(Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)

        self.logger.error("Max retries exceeded. Could not complete API call. Returning empty response.")
        return ("", 0, 0)

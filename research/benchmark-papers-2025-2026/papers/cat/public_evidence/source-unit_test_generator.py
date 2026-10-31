import json
import os
import re
import random

from command_executor import CommandExecutor
from coverage.jacoco_coverage import JacocoCoverage
from coverage.pycov_coverage import PycovCoverage
from error_message_parser import extract_error_message, extract_compilation_error_message_java
from file_preprocessor import FilePreprocessor
from lance_logger import LanceLogger
from model_invocation.llm_invocation import LLMInvocation
from prompt_builder import PromptBuilder
from utils import get_code_language
from yaml_parser_utils import load_yaml
from cfg.src.comex.codeviews.combined_graph.combined_driver import line_number_to_node_id_mapping
from cfg.src.comex.codeviews.CFG.CFG_driver import CFGDriver
from utils import read_file, add_random_suffix
from constants_config import MAX_TOKENS_NUM

def count_leading_spaces(text):
    match = re.match(r'^ +', text)
    if match:
        return len(match.group(0))
    return 0


def failed_test_to_string(failed_test: dict):
    failed_test_str = ""
    failed_test_dict = failed_test.get("code", {})
    error_message = failed_test.get("error_message", "")
    if failed_test_dict:
        failed_test_code = failed_test_dict.get("test_code", "").rstrip()
        failed_test_imports = (failed_test_dict.get("new_imports_code", "") or "").strip()
        failed_test_name = failed_test_dict.get("test_name", "").rstrip()
        failed_test_str += f"=========The failed test case is : {failed_test_name}=======\n"
        failed_test_str += f"{failed_test_code}\n"
        failed_test_str += f"additional imports: {failed_test_imports}\n"

        if error_message:
            failed_test_str += f"Failed with error message:\n{error_message}\n\n"
        else:
            failed_test_str += "\n\n"
    return failed_test_str


class UnitTestGenerator:
    def __init__(self, project_dir: str,
                 source_code_file: str,
                 test_code_file: str,
                 code_coverage_report_path: str,
                 test_execution_command: str,
                 llm_model: str,
                 test_code_command_dir: str = os.getcwd(),
                 test_dependencies: str = "",
                 included_files: list = None,
                 coverage_type="jacoco",
                 target_coverage: int = 100,
                 prompt_type: str = "baseline",
                 additional_instructions: str = ""):

        self.relevant_line_number_to_insert_tests_after = None
        self.relevant_line_number_to_insert_imports_after = None
        self.relevant_line_number_to_insert_tests_before = None
        self.test_headers_indentation = None
        self.lines_missed = None
        self.branch_missed = None
        self.current_coverage = None
        self.code_coverage_report = None
        self.project_dir = project_dir
        self.source_code_file = source_code_file
        self.test_code_file = test_code_file
        self.code_coverage_report_path = code_coverage_report_path
        self.test_execution_command = test_execution_command
        self.test_code_command_dir = test_code_command_dir
        self.test_dependencies = test_dependencies
        self.included_files = self.get_included_files(included_files)
        self.coverage_type = coverage_type
        self.target_coverage = target_coverage
        self.additional_instructions = additional_instructions
        self.language = get_code_language(source_code_file)

        self.llm_invoker = LLMInvocation(model=llm_model)

        self.logger = LanceLogger.initialize_logger(__name__)

        self.preprocessor = FilePreprocessor(self.test_code_file)
        self.failed_test_runs = []
        self.coverage_invalid_tests = []
        self.run_coverage()
        self.prompt_type = prompt_type
        self.path_history = {}
        # self.prompt = self.build_prompt(self.prompt_type)
        self.prompt = ""
        self.related_source_files = ""
        self.source_group = []

    def run_coverage(self):
        """
        run the build/test command and get the baseline coverage
        """
        self.logger.info(f'generate baseline coverage report: "{self.test_execution_command}"')
        try:
            stdout, stderr, exit_code, time_of_test_execution_command, command_duration = CommandExecutor.run_command(
                command=self.test_execution_command, cwd=self.test_code_command_dir
            )

            if exit_code != 0:
                raise RuntimeError(
                    f'Fatal: Error running test command. '
                    f'make sure this build command is correct: "{self.test_execution_command}"\n'
                    f'Exit code: {exit_code}'
                    f'\nStdout: {stdout}'
                    f'\nStderr: {stderr}'
                )

            # Instantiate Coverage and process the coverage report
            if self.coverage_type == "jacoco":
                coverage_processor = JacocoCoverage(
                    project_dir=self.project_dir,
                    file_path=self.code_coverage_report_path,
                    src_file_path=self.source_code_file)
            elif self.coverage_type == "pycov":
                coverage_processor = PycovCoverage(
                    file_path=self.code_coverage_report_path,
                    src_file_path=self.source_code_file)
            else:
                raise ValueError(f"Unsupported coverage type: {self.coverage_type}")

            # Use the process_coverage_report method of Coverage, passing in the time the test command was executed
            try:
                self.lines_missed, self.branch_missed, line_percentage, branch_percentage = (
                    coverage_processor.process_coverage_report(
                        time_of_test_execution_command=time_of_test_execution_command
                    )
                )

                # Process the extracted coverage metrics
                self.current_coverage = (line_percentage, branch_percentage)
                self.code_coverage_report = f"Lines missed: {self.lines_missed}\n" \
                                            f"Branches missed: {self.branch_missed}\n" \
                                            f"Line coverage: {round(line_percentage * 100, 2)}%\n" \
                                            f"Branch coverage: {round(branch_percentage * 100, 2)}%"
                self.logger.info(f"In run_coverage(), code coverage report:\n{self.code_coverage_report}")
            except AssertionError as error:
                if self.coverage_type == "jacoco" and self._should_default_to_zero_coverage(str(error)):
                    self._set_zero_coverage_baseline(
                        "JaCoCo report is missing and module has no test sources; defaulting baseline coverage to 0%."
                    )
                    return
                self.logger.error(f"Error in coverage processing: {error}")
                raise
            except (ValueError, NotImplementedError) as e:
                self.logger.warning(f"Error parsing coverage report: {e}")
                with open(self.code_coverage_report_path, "r") as f:
                    self.code_coverage_report = f.read()
        except Exception as e:
            self.logger.error(str(e))
            raise

    def _should_default_to_zero_coverage(self, error_message: str) -> bool:
        missing_report = "was not generated" in error_message or "was not updated" in error_message
        return missing_report and self._module_has_no_tests()

    def _module_has_no_tests(self) -> bool:
        test_root = os.path.join(self.project_dir, "src", "test")
        if not os.path.isdir(test_root):
            return True

        for _, _, files in os.walk(test_root):
            for filename in files:
                lower_name = filename.lower()
                if self.coverage_type == "jacoco":
                    if lower_name.endswith(".java") or lower_name.endswith(".kt"):
                        return False
                else:
                    if lower_name.startswith("test") and lower_name.endswith(".py"):
                        return False
        return True

    def _set_zero_coverage_baseline(self, reason: str):
        self.lines_missed = []
        self.branch_missed = []
        self.current_coverage = (0.0, 0.0)
        self.code_coverage_report = (
            "Lines missed: []\n"
            "Branches missed: []\n"
            "Line coverage: 0.0%\n"
            "Branch coverage: 0.0%"
        )
        self.logger.warning(reason)
        self.logger.info(f"In run_coverage(), code coverage report:\n{self.code_coverage_report}")

    @staticmethod
    def get_included_files(included_files):
        if included_files:
            included_files_content = []
            file_names = []
            for file_path in included_files:
                try:
                    with open(file_path, "r") as file:
                        included_files_content.append(file.read())
                        file_names.append(file_path)
                except IOError as e:
                    print(f"Error reading file {file_path}: {str(e)}")

            out_str = ""
            if included_files_content:
                for i, content in enumerate(included_files_content):
                    out_str += f"file_path: `{file_names[i]}`\ncontent:\n```\n{content}\n```\n"

            return out_str.strip()
        return ""

    def build_prompt(self, prompt_type, pick_two_paths=True) -> dict:
        """
        Returns:
            str: prompt that will be used for generating new tests
        """

        failed_test_runs_value = ""
        try:
            # Check for existence of failed tests:
            for failed_test in self.failed_test_runs:
                failed_test_str = failed_test_to_string(failed_test)
                failed_test_runs_value += failed_test_str
        except Exception as e:
            self.logger.error(f"Error processing failed test runs: {e}")
        self.failed_test_runs = []

        no_coverage_increase_tests_value = ""

        self.prompt_builder = PromptBuilder(
            project_dir=self.project_dir,
            source_code_file=self.source_code_file,
            test_code_file=self.test_code_file,
            code_coverage_report=self.code_coverage_report,
            included_files=self.included_files,
            additional_instructions=self.additional_instructions,
            failed_test_runs=failed_test_runs_value,
            coverage_invalid_tests=no_coverage_increase_tests_value,
            language=self.language,
            lines_missed=self.lines_missed,
            branch_missed=self.branch_missed,
            path_history=self.path_history,
            test_dependencies=self.test_dependencies
        )
        if prompt_type == "control":
            prompt = self.prompt_builder.build_prompt_cfa_guided(pick_two_paths)
            self.path_history = self.prompt_builder.get_current_path_history()
            # output prompt to log in a readable (non-JSON escaped) format
            self._log_prompt_readable("Control Flow Aware Guided", prompt)
            return prompt
        elif prompt_type == "plrd":
            prompt, relsrcf, srcg = self.prompt_builder.build_prompt_cg()
            self.related_source_files = relsrcf
            self.source_group = srcg
            # output prompt to log in a readable (non-JSON escaped) format
            return prompt
        elif prompt_type == "coverage":
            return self.prompt_builder.build_prompt(coverage_enabled=True)
        else:
            return self.prompt_builder.build_prompt(coverage_enabled=False)

    def obtain_imports(self):
        paths = self.source_group
        imports = set()  
        for path in paths:
            path = os.path.normpath(path)
            if 'src/main/java/' in path:
                idx = path.index('src/main/java/') + len('src/main/java/')
                package_path = path[idx:]
                if package_path.endswith('.java'):
                    class_name = os.path.basename(package_path).replace('.java', '')
                    package = os.path.dirname(package_path).replace(os.sep, '.')
                    try:
                        if os.path.exists(path):
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                source_code = f.read()
                            is_public = False
                            for line in source_code.split('\n'):
                                line = line.strip()
                                if line.startswith('//') or line.startswith('*'):
                                    continue
                                if re.search(rf'\bpublic\s+(?:abstract\s+)?(?:final\s+)?(?:sealed\s+)?class\s+{re.escape(class_name)}\b', line):
                                    is_public = True
                                    break

                            if is_public:
                                imports.add(f"import {package}.{class_name};")
                            else:
                                self.logger.debug(f"[DEBUG] Skipping non-public class: {package}.{class_name}")
                        else:
                            self.logger.warning(f"[DEBUG] File not found: {path}")
                    except Exception as e:
                        self.logger.warning(f"[DEBUG] Error checking if class {class_name} is public: {e}")
        return " ".join(imports)

    def initial_test_suite_analysis_AST(self):
        """
        Specifically, when we can use AST to extract the test headers indentation
        and the relevant line number to insert new tests.

        In the case, each test class has at least one existing test method.
        :return:
        """

        test_code = read_file(self.test_code_file)
        cfg_driver = CFGDriver(self.language, test_code, {"test_code": True})
        _, node_id_to_line_numbers_mapping = line_number_to_node_id_mapping(test_code, cfg_driver.CFG_nodes)
        last_import_id = cfg_driver.file_obj["imports"][-1]["id"]
        last_line_for_imports = node_id_to_line_numbers_mapping[last_import_id][-1]

        class_obj = cfg_driver.file_obj["class_objects"][0]
        class_declaration_id = class_obj["class_declaration"]["id"]
        class_declaration_start_line = node_id_to_line_numbers_mapping[class_declaration_id][0]

        last_method_declaration = class_obj["methods_under_test"][-1]
        last_method_start_id = last_method_declaration["method_declaration"]["id"]
        last_method_start_line = node_id_to_line_numbers_mapping[last_method_start_id][0]
        test_code_lines = test_code.split('\n')
        method_line_str = test_code_lines[last_method_start_line - 1]
        indents = count_leading_spaces(method_line_str)

        self.test_headers_indentation = indents
        self.relevant_line_number_to_insert_tests_before = last_method_start_line
        self.relevant_line_number_to_insert_imports_after = last_line_for_imports

    def _log_dict_readable_str(self, label: str, data: dict) -> str:
        """Pretty-print any dictionary with readable formatting and decoded newlines.

        Features:
        - Works with nested dicts, lists, and mixed structures (e.g., list of dicts).
        - Decodes escaped newlines (\\n) into real newlines.
        - Returns a formatted string and logs it.
        """

        def normalize(value):
            """Decode escaped newlines and recursively handle nested structures."""
            if isinstance(value, str):
                if "\\n" in value and "\n" not in value:
                    try:
                        return value.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        return value.replace("\\n", "\n")
                return value
            elif isinstance(value, dict):
                return {k: normalize(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [normalize(v) for v in value]
            else:
                return value

        def format_value(v, indent: int) -> str:
            """Format any value (string, dict, list) with proper indentation."""
            pad = "  " * indent
            if isinstance(v, dict):
                return "\n" + format_dict(v, indent + 1)
            elif isinstance(v, list):
                if not v:
                    return "[]"
                lines = []
                for item in v:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{pad}- {format_value(item, indent + 1).lstrip()}")
                    else:
                        lines.append(f"{pad}- {item}")
                return "\n" + "\n".join(lines)
            else:
                return str(v)

        def format_dict(d: dict, indent: int = 0) -> str:
            pad = "  " * indent
            lines = []
            for k, v in d.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{pad}{k}:{format_value(v, indent + 1)}")
                else:
                    lines.append(f"{pad}{k}: {v}")
            return "\n".join(lines)

        try:
            normalized = normalize(data)
            formatted = (
                f"\n===== {label.upper()} DICTIONARY =====\n"
                f"{format_dict(normalized)}\n"
                f"===== END {label.upper()} ====="
            )

            self.logger.info(formatted)
            return formatted

        except Exception as e:
            self.logger.warning(f"Failed to log dictionary readably: {e}")
            return f"Error logging dict ({label}): {e}"

    def _log_prompt_readable(self, label: str, prompt_dict: dict):
        """Pretty-print system/user prompt sections with real newlines.

        If the strings appear double-escaped (contain '\n' but not actual newlines), attempt a unicode_escape
        decode; on failure fall back to simple replacement. Truncates extremely long prompts for log safety while
        still writing full content to an optional side file if desired in the future.
        """
        try:
            system_part = prompt_dict.get("system", "")
            user_part = prompt_dict.get("user", "")

            def normalize(text: str) -> str:
                if "\n" in text and "\n".encode().decode() != text and "\n" in text and "\n" not in text.splitlines():
                    # heuristic: contains literal backslash-n but few real newlines
                    if "\\n" in text and "\n" not in text:
                        try:
                            return text.encode("utf-8").decode("unicode_escape")
                        except Exception:
                            return text.replace("\\n", "\n")
                return text

            system_part = normalize(system_part)
            user_part = normalize(user_part)

            self.logger.info(
                f"\n===== {label.upper()} SYSTEM PROMPT =====\n{system_part}\n"
                f"===== {label.upper()} USER PROMPT =====\n{user_part}\n"
                f"===== END {label.upper()} ====="
            )
        except Exception as e:
            self.logger.warning(f"Failed to log prompt readably: {e}")

    def _log_prompt_readable_str(self, label: str, prompt_dict: dict) -> str:
        try:
            system_part = prompt_dict.get("system", "")
            user_part = prompt_dict.get("user", "")

            def normalize(text: str) -> str:
                if "\\n" in text and "\n" not in text:
                    try:
                        return text.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        return text.replace("\\n", "\n")
                return text

            system_part = normalize(system_part)
            user_part = normalize(user_part)

            formatted = (
                f"\n===== {label.upper()} SYSTEM PROMPT =====\n{system_part}\n"
                f"===== {label.upper()} USER PROMPT =====\n{user_part}\n"
                f"===== END {label.upper()} ====="
            )

            return formatted

        except Exception as e:
            self.logger.warning(f"Failed to log prompt readably: {e}")
            return f"Error logging prompt ({label}): {e}"

    def generate_tests(self, g_label, max_tokens=MAX_TOKENS_NUM, pick_two_paths=True):
        self.prompt = self.build_prompt(self.prompt_type, pick_two_paths)
        # self.logger.info(f"{g_label}: {self.path_history}")
        self.logger.info(f"Generating {g_label} ...")
        tests_dict, token_count = self.generate_test_by_prompt_llm(self.prompt, max_tokens)
        return self.prompt, tests_dict, token_count

    def generate_init_tests(self, prompt_type='baseline', max_tokens=MAX_TOKENS_NUM):
        prompt = self.build_prompt(prompt_type)
        tests_dict, token_count = self.generate_test_by_prompt_llm(prompt, max_tokens)
        return prompt, tests_dict, token_count

    def generate_test_by_prompt_llm(self, prompt, max_tokens=MAX_TOKENS_NUM):
        response, prompt_token_count, response_token_count = (
            self.llm_invoker.call_model(prompt=prompt,
                                        max_tokens=max_tokens))
        self.logger.info(f"Total token count for LLM {self.llm_invoker.model}: "
                         f"{prompt_token_count + response_token_count}")
        token_count = prompt_token_count + response_token_count
        try:
            tests_dict = load_yaml(response, keys_fix_yaml=["test_code",
                                                            "test_name",
                                                            "test_behavior"], )
            if tests_dict is None:
                return {}
        except Exception as e:
            self.logger.error(f"Error during test generation: {e}")
            fail_details = {
                "status": "FAIL",
                "reason": f"Parsing error: {e}",
                "exit_code": None,  # No exit code as it's a parsing issue
                "stderr": str(e),
                "stdout": "",  # No output expected from a parsing error
                "test": response,  # Use the response that led to the error
            }
            # self.failed_test_runs.append(fail_details)
            tests_dict = []

        return tests_dict, token_count

    def validate_test(self, generated_test: dict):
        # Try to add the generated test to the relevant section in the original test file
        with open(self.test_code_file, "r") as test_file:
            original_content = test_file.read()  # Store original content
        try:
            processed_test, relevant_line_number_to_insert_imports_after, \
            relevant_line_number_to_insert_tests_before = self.add_new_test_to_test_file(generated_test, original_content)
            if processed_test:
                with open(self.test_code_file, "w") as test_file:
                    test_file.write(processed_test)
            else:
                # processed_test is empty - failed to add test to file
                self.logger.warning(f"Failed to process test - add_new_test_to_test_file returned empty result")
                failure_details = {
                    "status": "FAIL",
                    "reason": "Failed to process test code",
                    "exit_code": None,
                    "stderr": "add_new_test_to_test_file returned empty",
                    "stdout": "",
                    "test": generated_test,
                    "line_coverage": round(self.current_coverage[0] * 100, 2),
                    "branch_coverage": round(self.current_coverage[1] * 100, 2)
                }
                self.failed_test_runs.append({
                    "code": generated_test,
                    "error_message": "Failed to process test code - could not insert into test file"
                })
                return failure_details
            test_name = generated_test.get("test_name")
            # if test_name:
            #     # Now try to run the test so that we can check if the newly added test is valid
            #     self.logger.info(f'Run test with the command: "{self.test_execution_command}#{test_name}"')
            #     stdout, stderr, exit_code, time_of_command, command_duration = CommandExecutor.run_command(
            #         command=f"{self.test_execution_command}#{test_name}", cwd=self.test_code_command_dir, timeout=10
            #     )
            # else:
            # Now try to run the test so that we can check if the newly added test is valid
            self.logger.info(f'Run test with the command: "{self.test_execution_command}"')
            stdout, stderr, exit_code, time_of_command, command_duration = CommandExecutor.run_command(
                command=self.test_execution_command, cwd=self.test_code_command_dir, timeout=60
            )

            # Now we need to check if we were able to run the test successfully or not
            if exit_code != 0:
                # As the test failed, we go back to the test file with the original content
                with open(self.test_code_file, "w") as test_file:
                    test_file.write(original_content)
                if "COMPILATION ERROR" in stdout or "Compilation failed" in stdout:
                    self.logger.info(f"Test generated with compilation error.")
                    error_message = extract_compilation_error_message_java(stdout)
                    failure_details = {
                        "status": "FAIL",
                        "reason": "Compilation failure",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": error_message,
                        "test": generated_test,
                        "line_coverage": round(self.current_coverage[0] * 100, 2),
                        "branch_coverage": round(self.current_coverage[1] * 100, 2)
                    }
                    self.failed_test_runs.append({
                        "code": generated_test,
                        "error_message": error_message
                    })
                elif "Timeout" in stdout:
                    self.logger.info(f"Test generated failed due to timeout.")
                    failure_details = {
                        "status": "FAIL",
                        "reason": "Timeout",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": "Timeout",
                        "test": generated_test,
                        "line_coverage": round(self.current_coverage[0] * 100, 2),
                        "branch_coverage": round(self.current_coverage[1] * 100, 2)
                    }
                    self.failed_test_runs.append({
                        "code": generated_test,
                        "error_message": "Timeout"
                    })
                else:
                    self.logger.info(f"Test generated failed due to runtime error.")
                    error_message = extract_error_message(stdout, self.language)
                    failure_details = {
                        "status": "FAIL",
                        "reason": "Test failures",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": error_message,
                        "test": generated_test,
                        "line_coverage": round(self.current_coverage[0] * 100, 2),
                        "branch_coverage": round(self.current_coverage[1] * 100, 2)
                    }
                    self.failed_test_runs.append(
                        {
                            "code": generated_test,
                            "error_message": error_message
                        }
                    )

                return failure_details

            # Test passed (exit_code == 0) - return success details
            self.logger.info(f"Generated test has passed: {test_name}")
            pass_details = {
                "status": "PASS",
                "reason": "",
                "exit_code": exit_code,
                "stderr": stderr,
                "stdout": "",
                "test": generated_test,
                "line_coverage": round(self.current_coverage[0] * 100, 2),
                "branch_coverage": round(self.current_coverage[1] * 100, 2)
            }

            self.relevant_line_number_to_insert_tests_before = relevant_line_number_to_insert_tests_before
            self.relevant_line_number_to_insert_imports_after = relevant_line_number_to_insert_imports_after
            return pass_details
        except Exception as e:
            self.logger.error(f"Error validating test: {e}")
            with open(self.test_code_file, "w") as test_file:
                test_file.write(original_content)
            # Also add to failed_test_runs for the fixing stage
            self.logger.info(f"Test generated failed due exception: {e}.")
            self.failed_test_runs.append({
                "code": generated_test,
                "error_message": f"Exception during validation: {e}"
            })
            return {
                "status": "FAIL",
                "reason": f"Error validating test: {e}",
                "exit_code": None,
                "stderr": str(e),
                "stdout": "",
                "test": generated_test,
                "line_coverage": round(self.current_coverage[0] * 100, 2),
                "branch_coverage": round(self.current_coverage[1] * 100, 2)
            }

    def add_new_test_to_test_file(self, generated_test: dict, original_content):
        processed_test = ""
        test_code = generated_test.get("test_code", "").rstrip()
        
        # Debug: Log why test might not be added
        if not test_code:
            self.logger.warning(f"[DEBUG] add_new_test: test_code is empty or missing!")
            self.logger.warning(f"[DEBUG] generated_test keys: {list(generated_test.keys())}")
            return "", None, None
        
        test_code = add_random_suffix(test_code)
        additional_imports = (generated_test.get("new_imports_code", "") or "").strip()
        if additional_imports and additional_imports[0] == '"' and additional_imports[-1] == '"':
            additional_imports = additional_imports.strip('"')

        # check if additional_imports only contains '"':

        if additional_imports and additional_imports == '""':
            additional_imports = ""
        staticimports = self.obtain_imports()
        self.logger.info(f"Obtained imports: {staticimports}")
        if staticimports and staticimports not in original_content:
            if additional_imports:
                additional_imports = additional_imports + "\n" + staticimports
            else:
                additional_imports = staticimports

        relevant_line_number_to_insert_tests_before = self.relevant_line_number_to_insert_tests_before
        relevant_line_number_to_insert_imports_after = self.relevant_line_number_to_insert_imports_after

        needed_indent = self.test_headers_indentation

        # now we will remove the initial indent of test code, and insert the needed indent
        test_code_indented = test_code
        if needed_indent:
            initial_indent = len(test_code) - len(test_code.lstrip())
            delta_indent = int(needed_indent) - initial_indent
            if delta_indent > 0:
                test_code_indented = "\n".join(
                    [delta_indent * " " + line for line in test_code.split("\n")]
                )
        test_code_indented = "\n" + test_code_indented.strip("\n") + "\n"

        # Debug: Check why test might not be inserted
        if not test_code_indented.strip():
            self.logger.warning(f"[DEBUG] add_new_test: test_code_indented is empty after processing!")
            return "", None, None
        
        if not relevant_line_number_to_insert_tests_before:
            self.logger.warning(f"[DEBUG] add_new_test: relevant_line_number_to_insert_tests_before is not set!")
            self.logger.warning(f"[DEBUG] Make sure initial_test_suite_analysis_AST() was called successfully")
            return "", None, None

        if test_code_indented and relevant_line_number_to_insert_tests_before:
            original_content_lines = original_content.split("\n")
            test_code_lines = test_code_indented.split("\n")
            processed_test_lines = (
                    original_content_lines[:relevant_line_number_to_insert_tests_before - 1]
                    + test_code_lines
                    + original_content_lines[relevant_line_number_to_insert_tests_before - 1:]
            )
            relevant_line_number_to_insert_tests_before += len(test_code_lines)

            # additional imports for line 'relevant_line_number_to_insert_imports_after
            processed_test = "\n".join(processed_test_lines)
            if relevant_line_number_to_insert_imports_after and additional_imports and additional_imports not in processed_test:
                additional_imports_lines = additional_imports.split("\n")
                processed_test_lines = (
                        processed_test_lines[:relevant_line_number_to_insert_imports_after]
                        + additional_imports_lines
                        + processed_test_lines[relevant_line_number_to_insert_imports_after:]
                )
                relevant_line_number_to_insert_imports_after += len(additional_imports_lines)
                relevant_line_number_to_insert_tests_before += len(additional_imports_lines)

            processed_test = "\n".join(processed_test_lines)
        return processed_test, relevant_line_number_to_insert_imports_after, relevant_line_number_to_insert_tests_before

    def build_prompt_for_fixing(self) -> dict:
        """
        Returns:
            str: prompt that will be used for fixing the failed test case
        """
        self.logger.info(f"[DEBUG] build_prompt_for_fixing: {len(self.failed_test_runs)} failed tests to fix")
        failed_test_runs_value = ""
        # Check for existence of failed tests:
        for idx, failed_test in enumerate(self.failed_test_runs):
            failed_test_str = failed_test_to_string(failed_test)
            failed_test_runs_value += failed_test_str
            test_name = failed_test.get("code", {}).get("test_name", "unknown")
            error_preview = (failed_test.get("error_message", "")[:100] or "no error message")
            self.logger.debug(f"[DEBUG] Failed test #{idx+1}: {test_name} - Error: {error_preview}")

        prompt_builder = PromptBuilder(
            project_dir=self.project_dir,
            source_code_file=self.source_code_file,
            test_code_file=self.test_code_file,
            failed_test_runs=failed_test_runs_value,
            language=self.language,
            related_source_files=self.related_source_files
        )
        # reset failed tests
        self.failed_test_runs = []
        return prompt_builder.build_prompt_for_fixing()

    def fix_failed_tests(self, logprefix, f_label, iter_num, max_tokens=MAX_TOKENS_NUM):
        # Check for existence of failed tests, fix until failed tests are empty or at most 5 iterations
        self.logger.info(f"[DEBUG] fix_failed_tests called with {len(self.failed_test_runs)} failed tests")
        fix_results_list = []
        iter_count = 0
        token_count = 0
        while self.failed_test_runs and iter_count < iter_num:
            try:
                fixing_prompt = self.build_prompt_for_fixing()
                self.logger.info(f"Generating {f_label} ...")
                fixed_tests, tokens = self.generate_test_by_prompt_llm(fixing_prompt, max_tokens)
                self.logger.info(f"Generate {f_label} Done.\nfixed_tests:\n{fixed_tests}")
                iter_count += 1
                token_count += tokens
                for fixed_test in fixed_tests.get("new_tests", []):
                    test_result = self.validate_test(fixed_test)
                    test_result['label'] = f"{f_label}_{iter_count}"
                    fix_results_list.append(test_result)
            except Exception as e:
                self.logger.error(f"Error processing failed test runs: {e}")
                continue
        return fix_results_list, token_count

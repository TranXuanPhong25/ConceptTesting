"""Code Analyst with dual execution (CodeHacker Sec. 3.4.1, Appendix L).

Tools: run_python(script) -- isolated Python calculator; run_cpp(input) --
compile and run the *target* submission in the sandbox; finish(report).
The analyst never sees the standard solution (the paper keeps ground truth
in the environment).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

from codehacker_concept import prompts
from codehacker_concept.llm import LLM
from codehacker_concept.sandbox import RunResult, compile_cpp, run_binary, run_python

MAX_TURNS = 8
TOOL_NAMES = ("run_python", "run_cpp", "finish")
_CALL = re.compile(r"\b(run_python|run_cpp|finish)\s*\(")


@dataclass
class ToolCall:
    name: str
    argument: str


def parse_call(text: str) -> ToolCall | None:
    """Parse the last ``name(<python string literal>)`` call in a model turn."""
    matches = list(_CALL.finditer(text))
    for match in reversed(matches):
        start = match.start()
        tail = text[start:]
        closes = [i for i, ch in enumerate(tail) if ch == ")"]
        for close in closes:
            snippet = tail[: close + 1]
            try:
                tree = ast.parse(snippet, mode="eval")
            except SyntaxError:
                continue
            call = tree.body
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                continue
            if call.func.id != match.group(1):
                continue
            if len(call.args) == 1 and not call.keywords:
                try:
                    value = ast.literal_eval(call.args[0])
                except (ValueError, SyntaxError):
                    continue
                return ToolCall(call.func.id, str(value))
            if not call.args and len(call.keywords) == 1:
                try:
                    value = ast.literal_eval(call.keywords[0].value)
                except (ValueError, SyntaxError):
                    continue
                return ToolCall(call.func.id, str(value))
    return None


def format_run(result: RunResult, stdout_limit: int = 2000) -> str:
    stdout = result.stdout
    if len(stdout) > stdout_limit:
        stdout = stdout[:stdout_limit] + f"... [{len(result.stdout)} chars total]"
    stderr = result.stderr.strip()[:500]
    return (f'Stdout: "{stdout}", Stderr: "{stderr}", ExitCode: {result.exit_code}, '
            f"Verdict: {result.status}, Time: {result.cpu_ms} ms")


@dataclass
class AnalystResult:
    report: str
    transcript: list[dict[str, Any]] = field(default_factory=list)
    turns: int = 0
    finished: bool = False
    tool_counts: dict[str, int] = field(default_factory=dict)


def run_analyst(
    llm: LLM,
    description: str,
    target_code: str,
    time_limit_ms: int,
    memory_limit_mb: int,
    key: str,
    suffix: str = "",
    tag: str = "analyst",
    max_turns: int = MAX_TURNS,
) -> AnalystResult:
    system = prompts.render(prompts.APPENDIX_L_CODE_ANALYST, problem_description=description, target_code=target_code)
    system += prompts.render(prompts.GLUE_ANALYST_TOOL_FORMAT, max_turns=max_turns) + suffix
    messages: list[tuple[str, str]] = [("user", system)]
    compiled = compile_cpp(target_code)
    result = AnalystResult(report="")
    for turn in range(max_turns + 1):
        if turn == max_turns:
            messages.append(("user", "[System] You have no tool calls left. Call finish(...) now with your final report."))
        reply = llm.chat(messages, tag=tag, sample_key=f"{key}#t{turn}")
        text = reply.text
        messages.append(("assistant", text))
        call = parse_call(text)
        result.turns = turn + 1
        entry: dict[str, Any] = {"turn": turn, "model": text[-3000:]}
        if call is None:
            if reply.error:
                entry["error"] = reply.error
                result.transcript.append(entry)
                break
            observation = ("[Tool Output] Could not parse a tool call. Use exactly one of run_python(\"\"\"...\"\"\"), "
                           "run_cpp(\"\"\"...\"\"\") or finish(\"\"\"...\"\"\") after `Call:`.")
        else:
            result.tool_counts[call.name] = result.tool_counts.get(call.name, 0) + 1
            entry["call"] = {"name": call.name, "argument": call.argument[:4000]}
            if call.name == "finish":
                result.report = call.argument
                result.finished = True
                result.transcript.append(entry)
                break
            if call.name == "run_python":
                run = run_python(call.argument)
                out = run.stdout[:3000]
                observation = f"[Tool Output] {out}" + (f"\nStderr: {run.stderr[-800:]}" if run.stderr.strip() else "")
                if run.status == "TLE":
                    observation += "\n(Python timed out after 20 s)"
            else:
                stdin = call.argument if call.argument.endswith("\n") else call.argument + "\n"
                if len(stdin) > 20000:
                    observation = "[Tool Output] Input too large for run_cpp (limit 20 KB); use the generator for large tests."
                elif not compiled.ok or compiled.binary is None:
                    observation = "[Tool Output] Compilation error: " + compiled.error[-500:]
                else:
                    observation = "[Tool Output] " + format_run(run_binary(compiled.binary, stdin, time_limit_ms, memory_limit_mb))
        entry["observation"] = observation[:3000]
        result.transcript.append(entry)
        messages.append(("user", observation))
    if not result.finished:
        # fall back to the last model message as the report
        result.report = next((e["model"] for e in reversed(result.transcript) if e.get("model")), "")
    return result

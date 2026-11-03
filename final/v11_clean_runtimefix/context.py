from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class V11Context:
    task: dict[str, Any]
    human_eval: dict[str, Any]
    original_program: dict[str, Any]
    directory: Path
    calls: Any
    sandbox: Any
    mining: dict[str, Any] | None = None
    facts: dict[str, Any] | None = None
    bundle: dict[str, Any] | None = None
    arm_results: dict[str, Any] = field(default_factory=dict)

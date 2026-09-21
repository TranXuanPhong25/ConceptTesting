from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run import run


def test_local_c_fixture_has_a_target_hit_and_mutant_discriminator() -> None:
    result = run(mutations=3)

    assert result["valid_inputs"] == 6
    assert result["target_hits"] >= 1
    assert result["mutant_distinguished"] >= 1

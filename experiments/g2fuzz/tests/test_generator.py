from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator import BinaryFormat, Concept, mutate_valid, parse_input, synthesize_seed


def test_concept_seed_has_a_valid_header_checksum_and_target_prefix() -> None:
    seed = synthesize_seed(Concept(require_target_prefix=True, target_flag=True))
    parsed = parse_input(seed)

    assert parsed.version == 1
    assert parsed.flags & 1
    assert parsed.payload.startswith(b"BUG!")


def test_mutations_preserve_binary_format_invariants() -> None:
    seed = synthesize_seed(Concept())
    for mutated in mutate_valid(seed, count=24, seed=7):
        parsed = parse_input(mutated)
        assert parsed.payload_length == len(parsed.payload)
        assert BinaryFormat.checksum(mutated[:-1]) == mutated[-1]

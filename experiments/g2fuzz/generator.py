"""Concept-guided structured seed generation for the local G2FUZZ MVP."""

from __future__ import annotations

from dataclasses import dataclass
import random
import struct


MAGIC = b"G2FZ"
HEADER = struct.Struct(">4sBBH")


@dataclass(frozen=True)
class Concept:
    """Static format hints analogous to an LLM-synthesized input generator spec."""

    target_flag: bool = False
    require_target_prefix: bool = False
    payload_size: int = 12


@dataclass(frozen=True)
class ParsedInput:
    version: int
    flags: int
    payload_length: int
    payload: bytes


class BinaryFormat:
    @staticmethod
    def checksum(data: bytes) -> int:
        return sum(data) & 0xFF

    @classmethod
    def build(cls, *, flags: int, payload: bytes, version: int = 1) -> bytes:
        if not 0 <= flags <= 0xFF:
            raise ValueError("flags must fit in one byte")
        if len(payload) > 0xFFFF:
            raise ValueError("payload is too large")
        body = HEADER.pack(MAGIC, version, flags, len(payload)) + payload
        return body + bytes([cls.checksum(body)])


def parse_input(data: bytes) -> ParsedInput:
    if len(data) < HEADER.size + 1:
        raise ValueError("input is shorter than header and checksum")
    if BinaryFormat.checksum(data[:-1]) != data[-1]:
        raise ValueError("checksum mismatch")
    magic, version, flags, payload_length = HEADER.unpack(data[: HEADER.size])
    if magic != MAGIC:
        raise ValueError("magic mismatch")
    payload = data[HEADER.size:-1]
    if payload_length != len(payload):
        raise ValueError("declared payload length mismatch")
    return ParsedInput(version, flags, payload_length, payload)


def synthesize_seed(concept: Concept) -> bytes:
    if concept.payload_size < 4:
        raise ValueError("payload_size must be at least four")
    prefix = b"BUG!" if concept.require_target_prefix else b"DATA"
    payload = prefix + b"A" * (concept.payload_size - len(prefix))
    return BinaryFormat.build(flags=1 if concept.target_flag else 0, payload=payload)


def mutate_valid(data: bytes, *, count: int, seed: int) -> list[bytes]:
    """Mutate payload/flags, then reconstruct length and checksum from the AST-like form."""

    parsed = parse_input(data)
    rng = random.Random(seed)
    outputs: list[bytes] = []
    for _ in range(count):
        payload = bytearray(parsed.payload)
        index = rng.randrange(len(payload))
        payload[index] ^= rng.randrange(1, 256)
        flags = parsed.flags ^ (1 << rng.randrange(2))
        outputs.append(BinaryFormat.build(flags=flags, payload=bytes(payload), version=parsed.version))
    return outputs

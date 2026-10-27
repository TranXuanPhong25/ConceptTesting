"""Synthetic retrieval example; cleanup should preserve the ValueError."""


def parse_value():
    try:
        raise ValueError("invalid value")
    finally:
        return "done"

"""Synthetic retrieval example, not a benchmark bug or an upstream test."""


def collect(item, bucket=[]):
    """Contract: each call that omits bucket starts with an empty collection."""
    bucket.append(item)
    return bucket

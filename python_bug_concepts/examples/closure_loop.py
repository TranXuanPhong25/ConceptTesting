"""Synthetic retrieval example; callbacks should preserve their own index."""


def make_callbacks():
    callbacks = []
    for index in range(3):
        callbacks.append(lambda: index)
    return callbacks

from enum import StrEnum


class Device(StrEnum):
    """
    Inference device preference.
    """

    CPU = "cpu"
    CUDA = "cuda"

from enum import Enum, auto


class FileNameStrategy(Enum):
    """Strategy to use for naming files."""

    FILE_NAME = auto()
    """Save the asset with the file name in its href.

    Could potentially conflict with another asset with the same file name but
    different path.
    """

    KEY = auto()
    """Save the asset with its key as its file name."""


class ErrorStrategy(Enum):
    """Strategy to use when encountering errors during download."""

    KEEP = auto()
    """Keep the asset on the item with its original href."""

    DELETE = auto()
    """Delete the asset from the item."""

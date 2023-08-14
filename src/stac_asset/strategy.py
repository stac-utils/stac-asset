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


class DownloadStrategy(Enum):
    """Strategy to use when encountering errors during download."""

    ERROR = auto()
    """Throw an error if an asset cannot be downloaded."""

    KEEP = auto()
    """Warn, but keep the asset on the item."""

    DELETE = auto()
    """Warn, but delete the asset from the item."""

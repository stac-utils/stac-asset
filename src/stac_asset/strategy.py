from enum import Enum, auto


class FileNameStrategy(Enum):
    """Strategy to use when downloading assets."""

    FILE_NAME = auto()
    """Save the asset with the file name in its href.

    Could potentially conflict with another asset with the same file name but
    different path.
    """

    KEY = auto()
    """Save the asset with its key as its file name."""

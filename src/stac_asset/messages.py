from dataclasses import dataclass
from pathlib import Path

from yarl import URL


@dataclass
class Message:
    """A message about downloading."""


@dataclass
class StartAssetDownload(Message):
    """Sent when an asset starts downloading."""

    key: str
    """The asset key."""

    owner_id: str | None
    """The owner id."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""


@dataclass
class ErrorAssetDownload(Message):
    """Sent when an asset errors while downloading."""

    key: str
    """The asset key."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""

    error: Exception
    """The error."""


@dataclass
class SkipAssetDownload(Message):
    """Sent when an asset is skipped while downloading."""

    key: str
    """The asset key."""

    path: Path
    """The local path that the asset is being downloaded to."""


@dataclass
class FinishAssetDownload(Message):
    """Sent when an asset finishes downloading."""

    key: str
    """The asset key."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""


@dataclass
class WriteChunk(Message):
    """Sent when a chunk is written to disk."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""

    size: int
    """The number of bytes written."""


@dataclass
class OpenUrl(Message):
    """Sent when a url is first opened."""

    url: URL
    """The URL"""

    size: int | None
    """The file size."""

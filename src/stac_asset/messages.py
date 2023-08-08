from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from yarl import URL


@dataclass
class StartAssetDownload:
    """Sent when an asset starts downloading."""

    key: str
    """The asset key."""

    item_id: Optional[str]
    """The item id."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""


@dataclass
class ErrorAssetDownload:
    """Sent when an asset starts downloading."""

    key: str
    """The asset key."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""


@dataclass
class FinishAssetDownload:
    """Sent when an asset finishes downloading."""

    key: str
    """The asset key."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""


@dataclass
class WriteChunk:
    """Sent when a chunk is written to disk."""

    href: str
    """The asset href."""

    path: Path
    """The local path that the asset is being downloaded to."""

    size: int
    """The number of bytes written."""


@dataclass
class OpenUrl:
    """Sent when a url is first opened."""

    url: URL
    """The URL"""

    size: Optional[int]
    """The file size."""

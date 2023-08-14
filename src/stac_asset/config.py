from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from .errors import CannotIncludeAndExclude
from .strategy import DownloadStrategy, FileNameStrategy

DEFAULT_S3_REGION_NAME = "us-west-2"
DEFAULT_S3_RETRY_MODE = "adaptive"
DEFAULT_S3_MAX_ATTEMPTS = 10


@dataclass
class Config:
    """Configuration for downloading items and their assets."""

    alternate_assets: List[str] = field(default_factory=list)
    """Alternate asset keys to prefer, if available."""

    asset_file_name_strategy: FileNameStrategy = FileNameStrategy.FILE_NAME
    """The file name strategy to use when downloading assets."""

    download_strategy: DownloadStrategy = DownloadStrategy.ERROR
    """The strategy to use when errors occur during download."""

    exclude: List[str] = field(default_factory=list)
    """Assets to exclude from the download.

    Mutually exclusive with ``include``.
    """

    include: List[str] = field(default_factory=list)
    """Assets to include in the download.

    Mutually exclusive with ``exclude``.
    """

    make_directory: bool = True
    """Whether to create the output directory.

    If False, and the output directory does not exist, an error will be raised.
    """

    clean: bool = True
    """If true, clean up the downloaded file if it errors."""

    earthdata_token: Optional[str] = None
    """A token for logging in to Earthdata."""

    s3_region_name: str = DEFAULT_S3_REGION_NAME
    """Default s3 region."""

    s3_requester_pays: bool = False
    """If using the s3 client, enable requester pays."""

    s3_retry_mode: str = DEFAULT_S3_RETRY_MODE
    """The retry mode to use for s3 requests."""

    s3_max_attempts: int = DEFAULT_S3_MAX_ATTEMPTS
    """The maximum number of attempts when downloading assets from s3."""

    def validate(self) -> None:
        """Validates this configuration.

        Raises:
            CannotIncludeAndExclude: ``include`` and ``exclude`` are mutually exclusive
        """
        if self.include and self.exclude:
            raise CannotIncludeAndExclude(include=self.include, exclude=self.exclude)

    def copy(self) -> Config:
        """Returns a deep copy of this config.

        Returns:
            Config: A deep copy of this config.
        """
        return copy.deepcopy(self)

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from .errors import CannotIncludeAndExclude
from .strategy import FileNameStrategy


@dataclass
class Config:
    """Configuration for downloading items and their assets."""

    asset_file_name_strategy: FileNameStrategy = FileNameStrategy.FILE_NAME
    """The file name strategy to use when downloading assets."""

    exclude: List[str] = field(default_factory=list)
    """Assets to exclude from the download.

    Mutually exclusive with ``include``.
    """

    include: List[str] = field(default_factory=list)
    """Assets to include in the download.

    Mutually exclusive with ``exclude``.
    """

    file_name: Optional[str] = None
    """The file name of the output item.

    If not provided, the output item will not be saved.
    """

    make_directory: bool = True
    """Whether to create the output directory.

    If False, and the output directory does not exist, an error will be raised.
    """

    warn: bool = False
    """When downloading, warn instead of erroring."""

    s3_requester_pays: bool = False
    """If using the s3 client, enable requester pays."""

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

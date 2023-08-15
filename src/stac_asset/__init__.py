"""Read and download STAC items, item collections, collections, and assets.

The core class is :py:class:`Client`, which defines a common interface for
accessing assets. There are also some free functions, :py:func:`download_item`
and :py:func:`download_item_collection`, which provide simple one-shot
interfaces for downloading assets.

Writing items, item collections, collections, and assets is currently
unsupported, but is on the roadmap.
"""


from ._functions import (
    download_collection,
    download_item,
    download_item_collection,
)
from .client import Client
from .config import Config
from .earthdata_client import EarthdataClient
from .errors import (
    AssetOverwriteError,
    CannotIncludeAndExclude,
    ContentTypeError,
    DownloadError,
    DownloadWarning,
)
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .strategy import DownloadStrategy, FileNameStrategy

__all__ = [
    "DownloadWarning",
    "AssetOverwriteError",
    "CannotIncludeAndExclude",
    "Client",
    "Config",
    "ContentTypeError",
    "DownloadError",
    "DownloadStrategy",
    "EarthdataClient",
    "FileNameStrategy",
    "FilesystemClient",
    "HttpClient",
    "PlanetaryComputerClient",
    "S3Client",
    "download_collection",
    "download_item",
    "download_item_collection",
]

"""Read and download STAC items, item collections, and assets.

The core class is :py:class:`Client`, which defines a common interface for
accessing assets. There are also some free functions, :py:func:`download_item`
and :py:func:`download_item_collection`, which provide simple one-shot
interfaces for downloading assets.

Writing items, item collections, and assets is currently unsupported, but is on
the roadmap.
"""


from .client import Client
from .earthdata_client import EarthdataClient
from .errors import (
    AssetDownloadException,
    AssetDownloadWarning,
    AssetOverwriteException,
    CantIncludeAndExclude,
)
from .filesystem_client import FilesystemClient
from .functions import (
    download_item,
    download_item_collection,
    guess_client,
)
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .strategy import FileNameStrategy
from .usgs_eros_client import UsgsErosClient

__all__ = [
    "AssetDownloadWarning",
    "AssetDownloadException",
    "AssetOverwriteException",
    "CantIncludeAndExclude",
    "Client",
    "EarthdataClient",
    "FileNameStrategy",
    "FilesystemClient",
    "HttpClient",
    "PlanetaryComputerClient",
    "S3Client",
    "UsgsErosClient",
    "download_item",
    "download_item_collection",
    "guess_client",
]

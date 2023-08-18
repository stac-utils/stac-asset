"""Read and download STAC items, item collections, collections, and assets.

The main entry points are free functions:

* :py:func:`download_item`
* :py:func:`download_item_collection`
* :py:func:`download_collection`
* :py:func:`download_asset`

Use :py:class:`Config` to configure how assets are downloaded.  Every client
inherits from :py:class:`Client`, which defines a common interface for accessing
assets.  Writing items, item collections, collections, and assets is currently
unsupported, but is on the roadmap.
"""


from ._functions import (
    asset_exists,
    download_asset,
    download_collection,
    download_item,
    download_item_collection,
)
from .client import Client
from .config import Config
from .earthdata_client import EarthdataClient
from .errors import (
    AssetOverwriteError,
    ConfigError,
    ContentTypeError,
    DownloadError,
    DownloadWarning,
)
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .strategy import ErrorStrategy, FileNameStrategy

# Keep this list sorted
__all__ = [
    "AssetOverwriteError",
    "Client",
    "Config",
    "ConfigError",
    "ContentTypeError",
    "DownloadError",
    "DownloadWarning",
    "EarthdataClient",
    "ErrorStrategy",
    "FileNameStrategy",
    "FilesystemClient",
    "HttpClient",
    "PlanetaryComputerClient",
    "S3Client",
    "asset_exists",
    "download_asset",
    "download_collection",
    "download_item",
    "download_item_collection",
]

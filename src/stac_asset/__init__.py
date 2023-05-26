"""Get STAC Assets from various platforms and using different authentication schemes.

The core class is :py:class:`Client`, which defines a common interface.
Other clients inherit from :py:class:`Client` to implement any custom behavior.
"""


from .client import Client
from .earthdata_client import EarthdataClient
from .errors import (
    AssetDownloadException,
    AssetDownloadWarning,
    AssetOverwriteException,
)
from .filesystem_client import FilesystemClient
from .functions import (
    download_href,
    download_item,
    download_item_from_href,
    guess_client,
    open_href,
    read_file,
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
    "Client",
    "EarthdataClient",
    "FileNameStrategy",
    "FilesystemClient",
    "HttpClient",
    "PlanetaryComputerClient",
    "S3Client",
    "UsgsErosClient",
    "download_href",
    "download_item",
    "download_item_from_href",
    "guess_client",
    "open_href",
    "read_file",
]

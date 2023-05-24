from typing import AsyncIterator

from pystac import Asset

from .constants import DEFAULT_ASSET_FILE_NAME
from .http_client import HttpClient
from .s3_client import S3Client
from .types import PathLikeObject
from .usgs_eros_client import UsgsErosClient


async def open_href(href: str) -> AsyncIterator[bytes]:
    """Open a file at the given href.

    Args:
        href: The href to open.

    Returns:
        AsyncIterator[bytes]: An iterator over the file's bytes.
    """
    client = HttpClient()
    async for chunk in client.open_href(href):
        yield chunk


async def open_asset(asset: Asset) -> AsyncIterator[bytes]:
    """Open a STAC Asset.

    Args:
        asset: The Asset to open.

    Returns:
        AsyncIterator[bytes]: An iterator over the Asset's bytes.
    """
    client = HttpClient()
    async for chunk in client.open_href(asset.href):
        yield chunk


async def download_href(href: str, path: PathLikeObject) -> None:
    """Download a file to the given path.

    The path's directory must exist.

    Args:
        href: The href to download.
        path: The location of the downloaded file.
    """
    client = HttpClient()
    await client.download_href(href, path)


async def download_asset(
    asset: Asset,
    directory: PathLikeObject,
    make_directory: bool = False,
    asset_file_name: str = DEFAULT_ASSET_FILE_NAME,
) -> None:
    """Download a STAC Asset into the given directory.

    The file at the asset's href is downloaded into the directory. The asset is
    also downloaded into the directory, and its href is updated to point to the
    local file.

    Args:
        asset: The Asset to download.
        directory: The location of the downloaded file and Asset.
        make_directory: If true, create the directory (with exists_ok=True)
            before downloading.
    """
    client = HttpClient()
    await client.download_asset(asset, directory, make_directory, asset_file_name)


__all__ = [
    "HttpClient",
    "S3Client",
    "UsgsErosClient",
    "download_asset",
    "download_href",
    "open_asset",
    "open_href",
]

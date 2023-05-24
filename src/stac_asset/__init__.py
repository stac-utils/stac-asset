"""Get STAC Assets from various platforms and using different authentication schemes.

The core class is :py:class:`Client`, which defines a common interface.
Other clients inherit from :py:class:`Client` to implement any custom behavior.
"""

from typing import AsyncIterator, Optional

from pystac import Asset, Item
from yarl import URL

from .client import Client
from .constants import DEFAULT_ASSET_FILE_NAME
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
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
    client = await guess_client(href)
    async for chunk in client.open_href(href):
        yield chunk


async def open_asset(asset: Asset) -> AsyncIterator[bytes]:
    """Open a STAC Asset.

    Args:
        asset: The Asset to open.

    Returns:
        AsyncIterator[bytes]: An iterator over the Asset's bytes.
    """
    client = await guess_client(asset.href)
    async for chunk in client.open_href(asset.href):
        yield chunk


async def download_href(href: str, path: PathLikeObject) -> None:
    """Download a file to the given path.

    The path's directory must exist.

    Args:
        href: The href to download.
        path: The location of the downloaded file.
    """
    client = await guess_client(href)
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
    client = await guess_client(asset.href)
    await client.download_asset(asset, directory, make_directory, asset_file_name)


async def download_item(
    item: Item,
    directory: PathLikeObject,
    make_directory: bool = False,
    item_file_name: Optional[str] = None,
    include_self_link: bool = True,
) -> None:
    """Downloads an item to the local filesystem.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        make_directory: Whether to create the directory if it doesn't exist.
        item_file_name: The file name of the output item. If not provided, will
            default to the item's id with a .json extension.
        include_self_link: Whether to include a self link in the output item.
    """
    if not item.assets:
        raise ValueError("cannot guess a client if an item does not have any assets")
    client = await guess_client(next(iter(item.assets.values())).href)
    await client.download_item(
        item, directory, make_directory, item_file_name, include_self_link
    )


async def guess_client(href: str) -> Client:
    """Guess which client should be used to open the given href.

    Args:
        href: The input href.

    Returns:
        Client: The most appropriate client for the href, maybe.
    """
    url = URL(href)
    if not url.host:
        return FilesystemClient()
    if url.host.endswith("blob.core.windows.net"):
        return await PlanetaryComputerClient.default()
    if url.host == "https://landsatlook.usgs.gov":
        return await UsgsErosClient.default()
    elif url.scheme == "http" or url.scheme == "https":
        return await HttpClient.default()
    elif url.scheme == "s3":
        return S3Client()
    else:
        return FilesystemClient()


__all__ = [
    "FilesystemClient",
    "HttpClient",
    "PlanetaryComputerClient",
    "S3Client",
    "UsgsErosClient",
    "download_asset",
    "download_href",
    "download_item",
    "open_asset",
    "open_href",
]

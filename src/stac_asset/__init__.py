from typing import AsyncIterator, Optional

from pystac import Asset, Item

from .client import Client
from .constants import DEFAULT_ASSET_FILE_NAME
from .filesystem_client import FilesystemClient
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
    client = guess_client(href)
    async for chunk in client.open_href(href):
        yield chunk


async def open_asset(asset: Asset) -> AsyncIterator[bytes]:
    """Open a STAC Asset.

    Args:
        asset: The Asset to open.

    Returns:
        AsyncIterator[bytes]: An iterator over the Asset's bytes.
    """
    client = guess_client(asset.href)
    async for chunk in client.open_href(asset.href):
        yield chunk


async def download_href(href: str, path: PathLikeObject) -> None:
    """Download a file to the given path.

    The path's directory must exist.

    Args:
        href: The href to download.
        path: The location of the downloaded file.
    """
    client = guess_client(href)
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
    client = guess_client(asset.href)
    await client.download_asset(asset, directory, make_directory, asset_file_name)


async def download_item(
    item: Item,
    directory: PathLikeObject,
    make_directory: bool = False,
    item_file_name: Optional[str] = None,
    include_self_link: bool = True,
) -> None:
    if not item.assets:
        raise ValueError("cannot guess a client if an item does not have any assets")
    client = guess_client(next(iter(item.assets.values())).href)
    await client.download_item(
        item, directory, make_directory, item_file_name, include_self_link
    )


def guess_client(href: str) -> Client:
    if href.startswith("https://landsatlook.usgs.gov"):
        return UsgsErosClient()
    elif href.startswith("http"):
        return HttpClient()
    elif href.startswith("s3"):
        return S3Client()
    else:
        return FilesystemClient()


__all__ = [
    "HttpClient",
    "FilesystemClient",
    "S3Client",
    "UsgsErosClient",
    "download_asset",
    "download_href",
    "open_asset",
    "open_href",
]

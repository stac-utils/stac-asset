import json
from typing import AsyncIterator, Optional, Type

from pystac import Item
from yarl import URL

from .client import Client
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
    async with await guess_client(href) as client:
        async for chunk in client.open_href(href):
            yield chunk


async def download_href(href: str, path: PathLikeObject) -> None:
    """Download a file to the given path.

    The path's directory must exist.

    Args:
        href: The href to download.
        path: The location of the downloaded file.
    """
    async with await guess_client(href) as client:
        await client.download_href(href, path)


async def download_item(
    item: Item,
    directory: PathLikeObject,
    make_directory: bool = False,
    item_file_name: Optional[str] = None,
    include_self_link: bool = True,
) -> Item:
    """Downloads an item to the local filesystem.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        make_directory: Whether to create the directory if it doesn't exist.
        item_file_name: The file name of the output item. If not provided, will
            default to the item's id with a .json extension.
        include_self_link: Whether to include a self link in the output item.

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs.
    """
    if not item.assets:
        raise ValueError("cannot guess a client if an item does not have any assets")
    async with await guess_client(next(iter(item.assets.values())).href) as client:
        return await client.download_item(
            item, directory, make_directory, item_file_name, include_self_link
        )


async def download_item_from_href(
    href: str,
    directory: PathLikeObject,
    make_directory: bool = False,
    item_file_name: Optional[str] = None,
    include_self_link: bool = True,
) -> None:
    """Downloads an item from an href, then downloads its assets to the local
    filesystem.

    Args:
        href: The href to the :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        make_directory: Whether to create the directory if it doesn't exist.
        item_file_name: The file name of the output item. If not provided, will
            default to the item's id with a .json extension.
        include_self_link: Whether to include a self link in the output item.
    """
    data = json.loads(await read_file(href))
    item = Item.from_dict(data)
    item.set_self_href(href)
    await download_item(
        item, directory, make_directory, item_file_name, include_self_link
    )


async def read_file(
    href: str,
) -> bytes:
    """Reads all data from an href and returns the bytes.

    Uses :py:func:`guess_client` to determine the best client to use to read the bytes.

    Args:
        href: The href to the :py:class:`pystac.Item`.

    Returns:
        bytes: The data in the file
    """
    async with await guess_client(href) as client:
        data = b""
        async for chunk in client.open_href(href):
            data += chunk
        return data


async def guess_client(href: str) -> Client:
    """Guess which client should be used to open the given href.

    Args:
        href: The input href.

    Yields:
        Client: The most appropriate client for the href, maybe.
    """
    url = URL(href)
    if not url.host:
        client_type: Type[Client] = FilesystemClient
    elif url.host.endswith("blob.core.windows.net"):
        client_type = PlanetaryComputerClient
    elif url.host == "https://landsatlook.usgs.gov":
        client_type = UsgsErosClient
    elif url.scheme == "http" or url.scheme == "https":
        client_type = HttpClient
    elif url.scheme == "s3":
        client_type = S3Client
    else:
        client_type = FilesystemClient
    return await client_type.default()

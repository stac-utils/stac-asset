from typing import Optional

from pystac import Item, ItemCollection
from yarl import URL

from .client import Client
from .config import Config
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .types import PathLikeObject


async def download_item(
    item: Item,
    directory: PathLikeObject,
    config: Optional[Config] = None,
) -> Item:
    """Downloads an item to the local filesystem.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        config: The download configuration

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs.

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    if not item.assets:
        raise ValueError("cannot guess a client if an item does not have any assets")
    if config is None:
        config = Config()
    async with await guess_client(
        next(iter(item.assets.values())).href,
        s3_requester_pays=config.s3_requester_pays,
    ) as client:
        return await client.download_item(
            item=item,
            directory=directory,
            config=config,
        )


async def download_item_collection(
    item_collection: ItemCollection,
    directory: PathLikeObject,
    config: Optional[Config] = None,
) -> ItemCollection:
    """Downloads an item collection to the local filesystem.

    Args:
        item_collection: The item collection to download
        directory: The destination directory
        config: The download configuration

    Returns:
        ItemCollection: The item collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    if config is None:
        config = Config()
    if not item_collection.items:
        return item_collection
    elif not item_collection.items[0].assets:
        raise ValueError(
            "cannot guess a client if an item collection's first item does not have "
            "any assets"
        )
    async with await guess_client(
        next(iter(item_collection.items[0].assets.values())).href,
        s3_requester_pays=config.s3_requester_pays,
    ) as client:
        return await client.download_item_collection(
            item_collection,
            directory,
            config=config,
        )


async def guess_client(href: str, s3_requester_pays: bool = False) -> Client:
    """Guess which client should be used to open the given href.

    Args:
        href: The input href.
        s3_requester_pays: If there's a URL host, use the s3 client and enable
        requester pays

    Yields:
        Client: The most appropriate client for the href, maybe.
    """
    url = URL(href)
    # TODO enable matching on domain and protocol
    if not url.host:
        return await FilesystemClient.default()
    elif url.scheme == "s3" or s3_requester_pays:
        return S3Client(requester_pays=s3_requester_pays)
    elif url.host.endswith("blob.core.windows.net"):
        return await PlanetaryComputerClient.default()
    elif url.scheme == "http" or url.scheme == "https":
        return await HttpClient.default()
    else:
        return await FilesystemClient.default()

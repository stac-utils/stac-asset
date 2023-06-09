from typing import List, Optional

from pystac import Item, ItemCollection
from yarl import URL

from .client import Client
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .strategy import FileNameStrategy
from .types import PathLikeObject
from .usgs_eros_client import UsgsErosClient


async def download_item(
    item: Item,
    directory: PathLikeObject,
    *,
    make_directory: bool = False,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    item_file_name: Optional[str] = None,
    include_self_link: bool = True,
    s3_requester_pays: bool = False,
    warn_on_download_error: bool = False,
) -> Item:
    """Downloads an item to the local filesystem.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        make_directory: Whether to create the directory if it doesn't exist.
        include: Asset keys to download. If not provided, all asset keys
            will be downloaded.
        exclude: Asset keys to not download. If not provided, all asset keys
            will be downloaded.
        item_file_name: The file name of the output item. If not provided, will
            default to the item's id with a .json extension.
        include_self_link: Whether to include a self link in the output item.
        s3_requester_pays: If using the s3 client, enable requester pays
        warn_on_download_error: Instead of raising any errors encountered while
            downloading, warn and delete the asset from the item

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs.

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    if not item.assets:
        raise ValueError("cannot guess a client if an item does not have any assets")
    async with await guess_client(
        next(iter(item.assets.values())).href, s3_requester_pays=s3_requester_pays
    ) as client:
        return await client.download_item(
            item=item,
            directory=directory,
            make_directory=make_directory,
            include=include,
            exclude=exclude,
            item_file_name=item_file_name,
            include_self_link=include_self_link,
            warn_on_download_error=warn_on_download_error,
        )


async def download_item_collection(
    item_collection: ItemCollection,
    directory: PathLikeObject,
    *,
    make_directory: bool = False,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    item_collection_file_name: Optional[str] = "item-collection.json",
    asset_file_name_strategy: FileNameStrategy = FileNameStrategy.FILE_NAME,
    s3_requester_pays: bool = False,
    warn_on_download_error: bool = False,
) -> ItemCollection:
    """Downloads an item collection to the local filesystem.

    Args:
        item_collection: The item collection to download
        directory: The destination directory
        make_directory: Whether to make the directory if it does not exist
        include: Asset keys to download. If not provided, all asset keys
            will be downloaded.
        exclude: Asset keys to not download. If not provided, all asset keys
            will be downloaded.
        item_collection_file_name: The name of the item collection JSON file. If
            None, do not write the item collection, only download the assets.
        asset_file_name_strategy: The strategy to use for the asset file names
        s3_requester_pays: If using the s3 client, enable requester pays
        warn_on_download_error: Instead of raising any errors encountered while
            downloading, warn and delete the asset from the item

    Returns:
        ItemCollection: The item collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    if not item_collection.items:
        return item_collection
    elif not item_collection.items[0].assets:
        raise ValueError(
            "cannot guess a client if an item collection's first item does not have "
            "any assets"
        )
    async with await guess_client(
        next(iter(item_collection.items[0].assets.values())).href,
        s3_requester_pays=s3_requester_pays,
    ) as client:
        return await client.download_item_collection(
            item_collection,
            directory,
            include=include,
            exclude=exclude,
            make_directory=make_directory,
            item_collection_file_name=item_collection_file_name,
            asset_file_name_strategy=asset_file_name_strategy,
            warn_on_download_error=warn_on_download_error,
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
    elif url.host == "https://landsatlook.usgs.gov":
        return await UsgsErosClient.default()
    elif url.scheme == "http" or url.scheme == "https":
        return await HttpClient.default()
    else:
        return await FilesystemClient.default()

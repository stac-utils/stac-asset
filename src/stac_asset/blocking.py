"""Blocking interfaces for functions.

These should only be used from fully synchronous code. If you have _any_ async
code in your application, prefer the top-level functions.
"""

import asyncio
from pathlib import Path

from pystac import Asset, Collection, Item, ItemCollection

from . import _functions
from .client import Client, Clients
from .config import Config
from .types import MessageQueue, PathLikeObject


def download_item(
    item: Item,
    directory: PathLikeObject,
    file_name: str | None = None,
    infer_file_name: bool = True,
    config: Config | None = None,
    messages: MessageQueue | None = None,
    clients: list[Client] | None = None,
    keep_non_downloaded: bool = False,
    max_concurrent_downloads: int = _functions.DEFAULT_MAX_CONCURRENT_DOWNLOADS,
) -> Item:
    """Downloads an item to the local filesystem, synchronously.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        file_name: The name of the item file to save. If not provided, will not
            be saved.
        infer_file_name: If ``file_name`` is None, infer the file name from the
            item's id. This argument is unused if ``file_name`` is not None.
        config: The download configuration
        messages: An optional queue to use for progress reporting
        clients: Pre-configured clients to use for access
        keep_non_downloaded: Keep all assets on the item, even if they're not
            downloaded.
        max_concurrent_downloads: The maximum number of downloads that can be
            active at one time.

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs and self href.

    Raises:
        ValueError: Raised if the item doesn't have any assets.
    """
    return asyncio.run(
        _functions.download_item(
            item=item,
            directory=directory,
            file_name=file_name,
            infer_file_name=infer_file_name,
            config=config,
            messages=messages,
            clients=clients,
            keep_non_downloaded=keep_non_downloaded,
            max_concurrent_downloads=max_concurrent_downloads,
        )
    )


def download_collection(
    collection: Collection,
    directory: PathLikeObject,
    file_name: str | None = "collection.json",
    config: Config | None = None,
    messages: MessageQueue | None = None,
    clients: list[Client] | None = None,
    keep_non_downloaded: bool = False,
    max_concurrent_downloads: int = _functions.DEFAULT_MAX_CONCURRENT_DOWNLOADS,
) -> Collection:
    """Downloads a collection to the local filesystem, synchronously.

    Does not download the collection's items' assets -- use
    :py:func:`download_item_collection` to download multiple items.

    Args:
        collection: A pystac collection
        directory: The destination directory
        file_name: The name of the collection file to save. If not provided,
            will not be saved.
        config: The download configuration
        messages: An optional queue to use for progress reporting
        clients: Pre-configured clients to use for access
        keep_non_downloaded: Keep all assets on the item, even if they're not
            downloaded.
        max_concurrent_downloads: The maximum number of downloads that can be
            active at one time.

    Returns:
        Collection: The collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    return asyncio.run(
        _functions.download_collection(
            collection=collection,
            directory=directory,
            file_name=file_name,
            config=config,
            messages=messages,
            clients=clients,
            keep_non_downloaded=keep_non_downloaded,
            max_concurrent_downloads=max_concurrent_downloads,
        )
    )


def download_item_collection(
    item_collection: ItemCollection,
    directory: PathLikeObject,
    path_template: str | None = None,
    file_name: str | None = "item-collection.json",
    config: Config | None = None,
    messages: MessageQueue | None = None,
    clients: list[Client] | None = None,
    keep_non_downloaded: bool = False,
    max_concurrent_downloads: int = _functions.DEFAULT_MAX_CONCURRENT_DOWNLOADS,
) -> ItemCollection:
    """Downloads an item collection to the local filesystem, synchronously.

    Args:
        item_collection: The item collection to download
        directory: The destination directory
        path_template: String to be interpolated to specify where to store
            downloaded files.
        file_name: The name of the item collection file to save. If not
            provided, will not be saved.
        config: The download configuration
        messages: An optional queue to use for progress reporting
        clients: Pre-configured clients to use for access
        keep_non_downloaded: Keep all assets on the item, even if they're not
            downloaded.
        max_concurrent_downloads: The maximum number of downloads that can be
            active at one time.

    Returns:
        ItemCollection: The item collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    return asyncio.run(
        _functions.download_item_collection(
            item_collection=item_collection,
            directory=directory,
            file_name=file_name,
            config=config,
            messages=messages,
            clients=clients,
            keep_non_downloaded=keep_non_downloaded,
            path_template=path_template,
            max_concurrent_downloads=max_concurrent_downloads,
        )
    )


def download_asset(
    key: str,
    asset: Asset,
    path: Path,
    config: Config,
    messages: MessageQueue | None = None,
    clients: Clients | None = None,
) -> Asset:
    """Downloads an asset, synchronously.

    Args:
        key: The asset key
        asset: The asset
        path: The path to which the asset will be downloaded
        config: The download configuration
        messages: An optional queue to use for progress reporting
        clients: A async-safe cache of clients. If not provided, a new one
            will be created.

    Returns:
        Asset: The asset with an updated href

    Raises:
        ValueError: Raised if the asset does not have an absolute href
    """
    return asyncio.run(
        _functions.download_asset(
            key=key,
            asset=asset,
            path=path,
            config=config,
            messages=messages,
            clients=clients,
        )
    )


def assert_asset_exists(
    asset: Asset,
    config: Config | None = None,
    clients: list[Client] | None = None,
) -> None:
    """Asserts that an asset exists, synchronously.

    Raises the source error if it does not.

    Args:
        asset: The asset the check for existence
        config: The download configuration to use for the existence check
        clients: Any pre-configured clients to use for the existence check

    Raises:
        Exception: An exception from the underlying client.
    """
    asyncio.run(_functions.assert_asset_exists(asset, config, clients))


def asset_exists(
    asset: Asset,
    config: Config | None = None,
    clients: list[Client] | None = None,
) -> bool:
    """Returns true if an asset exists, synchronously.

    Args:
        asset: The asset the check for existence
        config: The download configuration to use for the existence check
        clients: Any pre-configured clients to use for the existence check

    Returns:
        bool: Whether the asset exists or not
    """
    return asyncio.run(_functions.asset_exists(asset, config, clients))


def read_href(
    href: str, config: Config | None = None, clients: list[Client] | None = None
) -> bytes:
    """Reads an href and returns its bytes.

    Args:
        href: The href to read
        config: The download configuration to use
        clients: Any pre-configured clients to use

    Returns:
        bytes: The bytes from the href
    """
    return asyncio.run(_functions.read_href(href, config, clients))


def download_file(
    href: str,
    destination: PathLikeObject,
    config: Config | None = None,
    clients: list[Client] | None = None,
) -> None:
    """Downloads a file collection to the local filesystem.

    Args:
        href: The source href
        destination: The destination file path
        config: The download configuration
        clients: Pre-configured clients to use for access
    """
    return asyncio.run(_functions.download_file(href, destination, config, clients))

import json
from asyncio import Queue
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    TypeVar,
)

import pystac.utils
from pystac import Collection, Item, ItemCollection, STACError

from ._download import Downloads
from .config import Config
from .types import PathLikeObject

# Needed until we drop Python 3.8
if TYPE_CHECKING:
    AnyQueue = Queue[Any]
else:
    AnyQueue = Queue


async def download_item(
    item: Item,
    directory: PathLikeObject,
    config: Optional[Config] = None,
    queue: Optional[AnyQueue] = None,
) -> Item:
    """Downloads an item to the local filesystem.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        config: The download configuration
        queue: An optional queue to use for progress reporting

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs and self href.

    Raises:
        ValueError: Raised if the item doesn't have any assets.
    """
    return await _download_stac_object(
        item, directory, config=config or Config(), queue=queue
    )


async def download_collection(
    collection: Collection,
    directory: PathLikeObject,
    config: Optional[Config] = None,
    queue: Optional[AnyQueue] = None,
) -> Collection:
    """Downloads a collection to the local filesystem.

    Does not download the collection's items' assets -- use
    :py:func:`download_item_collection` to download multiple items.

    Args:
        collection: A pystac collection
        directory: The destination directory
        config: The download configuration
        queue: An optional queue to use for progress reporting

    Returns:
        Collection: The collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    return await _download_stac_object(
        collection, directory, config or Config(), queue=queue
    )


async def download_item_collection(
    item_collection: ItemCollection,
    directory: PathLikeObject,
    config: Optional[Config] = None,
    queue: Optional[AnyQueue] = None,
) -> ItemCollection:
    """Downloads an item collection to the local filesystem.

    Args:
        item_collection: The item collection to download
        directory: The destination directory
        config: The download configuration
        queue: An optional queue to use for progress reporting

    Returns:
        ItemCollection: The item collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    if config is None:
        config = Config()
    async with Downloads(config) as downloads:
        for item in item_collection.items:
            item.set_self_href(None)
            root = Path(directory) / item.id
            await downloads.add(item, root)
        await downloads.download(queue)
    if config.file_name:
        dest_href = Path(directory) / config.file_name
        for item in item_collection.items:
            for asset in item.assets.values():
                asset.href = pystac.utils.make_relative_href(
                    asset.href, str(dest_href), start_is_dir=False
                )
        item_collection.save_object(dest_href=str(dest_href))

    return item_collection


_T = TypeVar("_T", Collection, Item)


async def _download_stac_object(
    stac_object: _T,
    directory: PathLikeObject,
    config: Config,
    queue: Optional[AnyQueue],
) -> _T:
    links = list()
    for link in stac_object.links:
        absolute_href = link.get_absolute_href()
        if absolute_href:
            link.target = absolute_href
            links.append(link)
    stac_object.links = links
    # Will fail if the stac object doesn't have a self href and there's
    # relative asset hrefs
    stac_object = _make_asset_hrefs_absolute(stac_object)

    if config.file_name:
        item_path = Path(directory) / config.file_name
        stac_object.set_self_href(str(item_path))
    else:
        item_path = None
        stac_object.set_self_href(item_path)

    async with Downloads(config) as downloads:
        await downloads.add(stac_object, Path(directory))
        await downloads.download(queue)

    self_href = stac_object.get_self_href()
    if self_href:
        _make_asset_hrefs_relative(stac_object)
        d = stac_object.to_dict(include_self_link=True, transform_hrefs=False)
        with open(self_href, "w") as f:
            json.dump(d, f)

    return stac_object


def _make_asset_hrefs_relative(stac_object: _T) -> _T:
    # Copied from
    # https://github.com/stac-utils/pystac/blob/381cf89fc25c15142fb5a187d905e22681de42a2/pystac/item.py#L284C5-L298C20
    # until a fix for https://github.com/stac-utils/pystac/issues/1199 is
    # released.
    self_href = stac_object.get_self_href()
    for asset in stac_object.assets.values():
        if pystac.utils.is_absolute_href(asset.href):
            if self_href is None:
                raise STACError(
                    "Cannot make asset HREFs relative " "if no self_href is set."
                )
            asset.href = pystac.utils.make_relative_href(asset.href, self_href)
    return stac_object


def _make_asset_hrefs_absolute(stac_object: _T) -> _T:
    # Copied from
    # https://github.com/stac-utils/pystac/blob/381cf89fc25c15142fb5a187d905e22681de42a2/pystac/item.py#L309C3-L319C1
    # until a fix for https://github.com/stac-utils/pystac/issues/1199 is
    # released.
    self_href = stac_object.get_self_href()
    for asset in stac_object.assets.values():
        if not pystac.utils.is_absolute_href(asset.href):
            if self_href is None:
                raise STACError(
                    "Cannot make asset HREFs absolute if no self_href is set."
                )
            asset.href = pystac.utils.make_absolute_href(asset.href, self_href)
    return stac_object

import json
from asyncio import Queue
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Union,
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
    file_name: Optional[str] = None,
    config: Optional[Config] = None,
    queue: Optional[AnyQueue] = None,
) -> Item:
    """Downloads an item to the local filesystem.

    Args:
        item: The :py:class:`pystac.Item`.
        directory: The output directory that will hold the items and assets.
        file_name: The name of the item file to save. If not provided, will not
            be saved.
        config: The download configuration
        queue: An optional queue to use for progress reporting

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs and self href.

    Raises:
        ValueError: Raised if the item doesn't have any assets.
    """
    async with Downloads(config or Config()) as downloads:
        await downloads.add(item, Path(directory), file_name)
        await downloads.download(queue)

    self_href = item.get_self_href()
    if self_href:
        _make_asset_hrefs_relative(item)
        d = item.to_dict(include_self_link=True, transform_hrefs=False)
        with open(self_href, "w") as f:
            json.dump(d, f)

    return item


async def download_collection(
    collection: Collection,
    directory: PathLikeObject,
    file_name: Optional[str] = None,
    config: Optional[Config] = None,
    queue: Optional[AnyQueue] = None,
) -> Collection:
    """Downloads a collection to the local filesystem.

    Does not download the collection's items' assets -- use
    :py:func:`download_item_collection` to download multiple items.

    Args:
        collection: A pystac collection
        directory: The destination directory
        file_name: The name of the collection file to save. If not provided,
            will not be saved.
        config: The download configuration
        queue: An optional queue to use for progress reporting

    Returns:
        Collection: The collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    async with Downloads(config or Config()) as downloads:
        await downloads.add(collection, Path(directory), file_name)
        await downloads.download(queue)

    self_href = collection.get_self_href()
    if self_href:
        _make_asset_hrefs_relative(collection)
        d = collection.to_dict(include_self_link=True, transform_hrefs=False)
        with open(self_href, "w") as f:
            json.dump(d, f)

    return collection


async def download_item_collection(
    item_collection: ItemCollection,
    directory: PathLikeObject,
    file_name: Optional[str] = None,
    config: Optional[Config] = None,
    queue: Optional[AnyQueue] = None,
) -> ItemCollection:
    """Downloads an item collection to the local filesystem.

    Args:
        item_collection: The item collection to download
        directory: The destination directory
        file_name: The name of the item collection file to save. If not
            provided, will not be saved.
        config: The download configuration
        queue: An optional queue to use for progress reporting

    Returns:
        ItemCollection: The item collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    async with Downloads(config or Config()) as downloads:
        for item in item_collection.items:
            item.set_self_href(None)
            root = Path(directory) / item.id
            await downloads.add(item, root, None)
        await downloads.download(queue)
    if file_name:
        dest_href = Path(directory) / file_name
        for item in item_collection.items:
            for asset in item.assets.values():
                asset.href = pystac.utils.make_relative_href(
                    asset.href, str(dest_href), start_is_dir=False
                )
        item_collection.save_object(dest_href=str(dest_href))

    return item_collection


def _make_asset_hrefs_relative(
    stac_object: Union[Item, Collection]
) -> Union[Item, Collection]:
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

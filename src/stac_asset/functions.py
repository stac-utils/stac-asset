import asyncio
import os.path
import warnings
from pathlib import Path
from typing import Dict, Optional, Set, Tuple, Type

import pystac.utils
from pystac import Asset, Item, ItemCollection
from yarl import URL

from .client import Client
from .config import Config
from .errors import (
    AssetOverwriteError,
    DownloadError,
    DownloadWarning,
)
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .strategy import FileNameStrategy
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
        Item: The `~pystac.Item`, with the updated asset hrefs and self href.

    Raises:
        ValueError: Raised if the item doesn't have any assets.
    """
    if not item.assets:
        raise ValueError(f"no assets to download for item with id '{item.id}")
    else:
        # Will fail if the item doesn't have a self href and there's relative
        # asset hrefs
        item.make_asset_hrefs_absolute()

    if config is None:
        config = Config()
    else:
        config.validate()

    directory_as_path = Path(directory)
    if not directory_as_path.exists():
        if config.make_directory:
            directory_as_path.mkdir(parents=True)
        else:
            raise FileNotFoundError(f"output directory does not exist: {directory}")

    if config.file_name:
        item_path = directory_as_path / config.file_name
    else:
        self_href = item.get_self_href()
        if self_href:
            item_path = directory_as_path / os.path.basename(self_href)
        else:
            item_path = None
    item.set_self_href(str(item_path))

    file_names: Set[str] = set()
    assets: Dict[str, Tuple[Asset, Path]] = dict()
    for key, asset in (
        (k, a)
        for k, a in item.assets.items()
        if (not config.include or k in config.include)
        and (not config.exclude or k not in config.exclude)
    ):
        if config.asset_file_name_strategy == FileNameStrategy.FILE_NAME:
            file_name = os.path.basename(URL(asset.href).path)
        elif config.asset_file_name_strategy == FileNameStrategy.KEY:
            file_name = key + Path(asset.href).suffix

        if file_name in file_names:
            raise AssetOverwriteError(list(file_names))
        else:
            file_names.add(file_name)

        path = directory_as_path / file_name
        assets[key] = (asset, path)

    tasks = dict()
    clients: Dict[Type[Client], Client] = dict()
    for key, (asset, path) in assets.items():
        client_class = guess_client_class(asset, config)
        if client_class in clients:
            client = clients[client_class]
        else:
            client = await client_class.from_config(config)
            clients[client_class] = client
        tasks[key] = asyncio.create_task(
            client.download_asset(key, asset.clone(), path)
        )
        if item.get_self_href():
            item.assets[key].href = pystac.utils.make_relative_href(
                str(path), str(item_path)
            )
        else:
            item.assets[key].href = str(path.absolute())

    # TODO support fast failing
    exceptions = list()
    for key, task in tasks.items():
        try:
            _ = await task
        except Exception as exception:
            if config.warn:
                warnings.warn(str(exception), DownloadWarning)
                del item.assets[key]
            else:
                exceptions.append(exception)

    for client in clients.values():
        await client.close()

    if exceptions:
        raise DownloadError(exceptions)

    if item.get_self_href():
        item.save_object(include_self_link=True)

    return item


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

    directory_as_path = Path(directory)
    if not directory_as_path.exists():
        if config.make_directory:
            directory_as_path.mkdir(parents=True)
        else:
            raise FileNotFoundError(f"output directory does not exist: {directory}")

    tasks = list()
    for item in item_collection.items:
        # TODO what happens if items share ids?
        item_directory = directory_as_path / item.id
        item_config = config.copy()
        item_config.make_directory = True
        item_config.file_name = None

        # TODO we should share clients among items
        tasks.append(
            asyncio.create_task(
                download_item(
                    item=item,
                    directory=item_directory,
                    config=item_config,
                )
            )
        )
    results = await asyncio.gather(*tasks, return_exceptions=True)
    exceptions = list()
    for result in results:
        if isinstance(result, Exception):
            exceptions.append(result)
    if exceptions:
        raise DownloadError(exceptions)
    item_collection.items = results
    if config.file_name:
        item_collection.save_object(dest_href=str(directory_as_path / config.file_name))

    return item_collection


def guess_client_class(asset: Asset, config: Config) -> Type[Client]:
    """Guess which client should be used to download the given asset.

    If the configuration has ``alternate_assets``, these will be used instead of
    the asset's href, if present. The asset's href will be updated with the href picked.

    Args:
        asset: The asset
        config: A download configuration

    Returns:
        Client: The most appropriate client class for the href, maybe.
    """
    alternate = asset.extra_fields.get("alternate")
    if not isinstance(alternate, dict):
        alternate = None
    if alternate and config.alternate_assets:
        for alternate_asset in config.alternate_assets:
            if alternate_asset in alternate:
                try:
                    href = alternate[alternate_asset]["href"]
                    asset.href = href
                    return guess_client_class_from_href(href)
                except KeyError:
                    raise ValueError(
                        "invalid alternate asset definition (missing href): "
                        f"{alternate}"
                    )
    return guess_client_class_from_href(asset.href)


def guess_client_class_from_href(href: str) -> Type[Client]:
    """Guess the client class from an href.

    Args:
        href: An href

    Returns:
        A client class type.
    """
    url = URL(href)
    if not url.host:
        return FilesystemClient
    elif url.scheme == "s3":
        return S3Client
    elif url.host.endswith("blob.core.windows.net"):
        return PlanetaryComputerClient
    elif url.scheme == "http" or url.scheme == "https":
        return HttpClient
    else:
        raise ValueError(f"could not guess client class for href: {href}")

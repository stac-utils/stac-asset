from __future__ import annotations

import asyncio
import json
import os.path
import warnings
from asyncio import Semaphore, Task
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import pystac.utils
from pystac import Asset, Collection, Item, ItemCollection, Link, STACError
from pystac.layout import LayoutTemplate
from yarl import URL

from .client import Client, Clients
from .config import Config
from .errors import AssetOverwriteError, DownloadError, DownloadWarning
from .messages import (
    ErrorAssetDownload,
    FinishAssetDownload,
    SkipAssetDownload,
    StartAssetDownload,
)
from .strategy import ErrorStrategy, FileNameStrategy
from .types import MessageQueue, PathLikeObject

DEFAULT_MAX_CONCURRENT_DOWNLOADS: int = 500
"""The default number of downloads that can be active at once."""


@dataclass
class Download:
    owner: Item | Collection
    key: str
    asset: Asset
    path: Path
    clients: Clients
    config: Config

    async def download(
        self, messages: MessageQueue | None, stream: bool | None = None
    ) -> Download | WrappedError:
        if not os.path.exists(self.path) or self.config.overwrite:
            try:
                await download_asset(
                    self.key,
                    self.asset,
                    self.path,
                    config=self.config,
                    messages=messages,
                    clients=self.clients,
                    stream=stream,
                )
            except Exception as error:
                if self.config.fail_fast:
                    raise error
                else:
                    return WrappedError(self, error)
        else:
            if messages:
                await messages.put(SkipAssetDownload(key=self.key, path=self.path))

        self.asset.href = str(self.path)
        return self


class Downloads:
    def __init__(
        self,
        config: Config,
        clients: list[Client] | None = None,
        max_concurrent_downloads: int = DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    ) -> None:
        config.validate()
        self.config = config
        self.downloads: list[Download] = list()
        self.clients = Clients(config, clients)
        self.semaphore = Semaphore(max_concurrent_downloads)

    async def add(
        self,
        stac_object: Item | Collection,
        root: Path,
        file_name: str | None,
        keep_non_downloaded: bool,
    ) -> None:
        stac_object = make_link_hrefs_absolute(stac_object)
        # Will fail if the stac object doesn't have a self href and there's
        # relative asset hrefs
        stac_object = make_asset_hrefs_absolute(stac_object)
        if self_href := stac_object.get_self_href():
            stac_object.add_link(Link(rel="derived_from", target=self_href))
        if file_name:
            stac_object.set_self_href(str(Path(root) / file_name))
        else:
            stac_object.set_self_href(None)

        asset_file_names: set[str] = set()
        assets = dict()
        for key, asset in (
            (k, a)
            for k, a in stac_object.assets.items()
            if (not self.config.include or k in self.config.include)
            and (not self.config.exclude or k not in self.config.exclude)
        ):
            if self.config.file_name_strategy == FileNameStrategy.FILE_NAME:
                asset_file_name = os.path.basename(URL(asset.href).path)
            elif self.config.file_name_strategy == FileNameStrategy.KEY:
                asset_file_name = key + Path(asset.href).suffix
            else:
                raise ValueError(
                    f"unexpected file name strategy: {self.config.file_name_strategy}"
                )
            if asset_file_name in asset_file_names:
                raise AssetOverwriteError(list(asset_file_names))

            asset_file_names.add(asset_file_name)
            assets[key] = asset
            self.downloads.append(
                Download(
                    owner=stac_object,
                    key=key,
                    asset=asset,
                    path=root / asset_file_name,
                    clients=self.clients,
                    config=self.config,
                )
            )
        if keep_non_downloaded:
            stac_object.assets.update(assets)
        else:
            stac_object.assets = assets

    async def download(
        self, messages: MessageQueue | None, stream: bool | None = None
    ) -> None:
        tasks: set[Task[Download | WrappedError]] = set()
        for download in self.downloads:
            task = asyncio.create_task(
                self.download_with_lock(download, messages, stream)
            )
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        try:
            results = await asyncio.gather(*tasks)
        except Exception as error:
            # We failed fast
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise error

        exceptions = list()
        for result in results:
            if isinstance(result, WrappedError):
                if self.config.error_strategy == ErrorStrategy.DELETE:
                    del result.download.owner.assets[result.download.key]
                else:
                    # Simple check to make sure we haven't added other
                    # strategies that we're not handling
                    assert self.config.error_strategy == ErrorStrategy.KEEP

                if self.config.warn:
                    warnings.warn(str(result.error), DownloadWarning)
                else:
                    exceptions.append(result.error)
        if exceptions:
            raise DownloadError(exceptions)

    async def download_with_lock(
        self,
        download: Download,
        messages: MessageQueue | None,
        stream: bool | None = None,
    ) -> Download | WrappedError:
        await self.semaphore.acquire()
        try:
            return await download.download(messages=messages, stream=stream)
        finally:
            self.semaphore.release()

    async def __aenter__(self) -> Downloads:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.clients.close_all()


class WrappedError:
    download: Download
    error: Exception

    def __init__(self, download: Download, error: Exception) -> None:
        self.download = download
        self.error = error


async def download_item(
    item: Item,
    directory: PathLikeObject,
    file_name: str | None = None,
    infer_file_name: bool = True,
    config: Config | None = None,
    messages: MessageQueue | None = None,
    clients: list[Client] | None = None,
    keep_non_downloaded: bool = False,
    max_concurrent_downloads: int = DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    stream: bool | None = None,
) -> Item:
    """Downloads an item to the local filesystem.

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
        stream: If enabled, it iterates over the bytes of the response;
            otherwise, it reads the entire file into memory

    Returns:
        Item: The `~pystac.Item`, with the updated asset hrefs and self href.

    Raises:
        ValueError: Raised if the item doesn't have any assets.
    """
    if file_name is None and infer_file_name:
        file_name = f"{item.id}.json"

    async with Downloads(
        config=config or Config(),
        clients=clients,
        max_concurrent_downloads=max_concurrent_downloads,
    ) as downloads:
        await downloads.add(item, Path(directory), file_name, keep_non_downloaded)
        await downloads.download(messages, stream)

    self_href = item.get_self_href()
    if self_href:
        make_asset_hrefs_relative(item)
        d = item.to_dict(include_self_link=True, transform_hrefs=False)
        os.makedirs(os.path.dirname(self_href), exist_ok=True)
        with open(self_href, "w") as f:
            json.dump(d, f)

    return item


async def download_collection(
    collection: Collection,
    directory: PathLikeObject,
    file_name: str | None = "collection.json",
    config: Config | None = None,
    messages: MessageQueue | None = None,
    clients: list[Client] | None = None,
    keep_non_downloaded: bool = False,
    max_concurrent_downloads: int = DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    stream: bool = True,
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
        messages: An optional queue to use for progress reporting
        clients: Pre-configured clients to use for access
        keep_non_downloaded: Keep all assets on the item, even if they're not
            downloaded.
        max_concurrent_downloads: The maximum number of downloads that can be
            active at one time.
        stream: If enabled, it iterates over the bytes of the response;
            otherwise, it reads the entire file into memory

    Returns:
        Collection: The collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    async with Downloads(
        config=config or Config(),
        clients=clients,
        max_concurrent_downloads=max_concurrent_downloads,
    ) as downloads:
        await downloads.add(collection, Path(directory), file_name, keep_non_downloaded)
        await downloads.download(messages, stream)

    self_href = collection.get_self_href()
    if self_href:
        make_asset_hrefs_relative(collection)
        d = collection.to_dict(include_self_link=True, transform_hrefs=False)
        with open(self_href, "w") as f:
            json.dump(d, f)

    return collection


async def download_item_collection(
    item_collection: ItemCollection,
    directory: PathLikeObject,
    path_template: str | None = None,
    file_name: str | None = "item-collection.json",
    config: Config | None = None,
    messages: MessageQueue | None = None,
    clients: list[Client] | None = None,
    keep_non_downloaded: bool = False,
    max_concurrent_downloads: int = DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    stream: bool | None = None,
) -> ItemCollection:
    """Downloads an item collection to the local filesystem.

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
        stream: If enabled, it iterates over the bytes of the response;
            otherwise, it reads the entire file into memory

    Returns:
        ItemCollection: The item collection, with updated asset hrefs

    Raises:
        CantIncludeAndExclude: Raised if both include and exclude are not None.
    """
    layout_template = LayoutTemplate(
        path_template if path_template is not None else "${id}"
    )
    async with Downloads(
        config=config or Config(),
        clients=clients,
        max_concurrent_downloads=max_concurrent_downloads,
    ) as downloads:
        for item in item_collection.items:
            item.set_self_href(None)
            root = Path(directory) / layout_template.substitute(item)
            await downloads.add(item, root, None, keep_non_downloaded)
        await downloads.download(messages, stream)
    if file_name:
        dest_href = Path(directory) / file_name
        for item in item_collection.items:
            for asset in item.assets.values():
                asset.href = pystac.utils.make_absolute_href(
                    asset.href, start_is_dir=True
                )
        item_collection.save_object(dest_href=str(dest_href))

    return item_collection


async def download_asset(
    key: str,
    asset: Asset,
    path: Path,
    config: Config,
    messages: MessageQueue | None = None,
    clients: Clients | None = None,
    stream: bool | None = None,
) -> Asset:
    """Downloads an asset.

    Args:
        key: The asset key
        asset: The asset
        path: The path to which the asset will be downloaded
        config: The download configuration
        messages: An optional queue to use for progress reporting
        clients: A async-safe cache of clients. If not provided, a new one
            will be created.
        stream: If enabled, it iterates over the bytes of the response;
            otherwise, it reads the entire file into memory

    Returns:
        Asset: The asset with an updated href

    Raises:
        ValueError: Raised if the asset does not have an absolute href
    """
    if clients is None:
        clients = Clients(config)

    if not path.parent.exists():
        if config.make_directory:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"output directory does not exist: {path.parent}")

    href = get_absolute_asset_href(
        asset=asset, alternate_assets=config.alternate_assets
    )
    if href is None:
        raise ValueError(f"asset '{key}' does not have an absolute href: {asset.href}")
    client = await clients.get_client(href)

    if messages:
        if asset.owner:
            assert isinstance(asset.owner, (Item, Collection))
            owner_id = asset.owner.id
        else:
            owner_id = None
        await messages.put(
            StartAssetDownload(key=key, href=href, path=path, owner_id=owner_id)
        )
    try:
        await client.download_href(
            href,
            path,
            clean=config.clean,
            content_type=asset.media_type,
            messages=messages,
            stream=stream,
        )
    except Exception as error:
        if messages:
            await messages.put(
                ErrorAssetDownload(key=key, href=href, path=path, error=error)
            )
        raise error

    asset.href = str(path)
    if messages:
        await messages.put(FinishAssetDownload(key=key, href=href, path=path))
    return asset


async def assert_asset_exists(
    asset: Asset,
    config: Config | None = None,
    clients: list[Client] | None = None,
) -> None:
    """Asserts that an asset exists.

    Raises the source error if it does not.

    Args:
        asset: The asset the check for existence
        config: The download configuration to use for the existence check
        clients: Any pre-configured clients to use for the existence check

    Raises:
        Exception: An exception from the underlying client.
    """
    if config is None:
        config = Config()
    clients_ = Clients(config, clients=clients)
    href = get_absolute_asset_href(asset, config.alternate_assets)
    if href:
        client = await clients_.get_client(href)
        await client.assert_href_exists(href)
    else:
        raise ValueError("asset does not have an absolute href")


async def asset_exists(
    asset: Asset,
    config: Config | None = None,
    clients: list[Client] | None = None,
) -> bool:
    """Returns true if an asset exists.

    Args:
        asset: The asset the check for existence
        config: The download configuration to use for the existence check
        clients: Any pre-configured clients to use for the existence check

    Returns:
        bool: Whether the asset exists or not
    """
    try:
        await assert_asset_exists(asset, config, clients)
    except Exception:
        return False
    else:
        return True


async def open_href(
    href: str, config: Config | None = None, clients: list[Client] | None = None
) -> AsyncIterator[bytes]:
    """Opens an href and yields byte chunks.

    Args:
        href: The href to read
        config: The download configuration to use
        clients: Any pre-configured clients to use

    Yields:
        bytes: The bytes from the href
    """
    if config is None:
        config = Config()
    clients_ = Clients(config, clients=clients)
    async with await clients_.get_client(href) as client:
        async for chunk in client.open_href(href):
            yield chunk


async def read_href(
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
    data = b""
    async for chunk in open_href(href, config=config, clients=clients):
        data += chunk
    return data


def make_asset_hrefs_relative(
    stac_object: Item | Collection,
) -> Item | Collection:
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


def make_asset_hrefs_absolute(
    stac_object: Item | Collection,
) -> Item | Collection:
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


def make_link_hrefs_absolute(
    stac_object: Item | Collection, drop: bool = True
) -> Item | Collection:
    # This could be in pystac w/ STACObject as the input+output type
    links = list()
    for link in stac_object.links:
        absolute_href = link.get_absolute_href()
        if absolute_href:
            link.target = absolute_href
            links.append(link)
        elif not drop:
            raise ValueError(f"cannot make link's href absolute: {link}")
    stac_object.links = links
    return stac_object


def get_absolute_asset_href(asset: Asset, alternate_assets: list[str]) -> str | None:
    alternate = asset.extra_fields.get("alternate")
    if not isinstance(alternate, dict):
        alternate = None
    if alternate and alternate_assets:
        for alternate_asset in alternate_assets:
            if alternate_asset in alternate:
                try:
                    href = alternate[alternate_asset]["href"]
                    if asset.owner:
                        start_href = asset.owner.get_self_href()
                    else:
                        start_href = None
                    return pystac.utils.make_absolute_href(
                        href, start_href, start_is_dir=False
                    )
                except KeyError:
                    raise ValueError(
                        "invalid alternate asset definition (missing href): "
                        f"{alternate}"
                    )
    return asset.get_absolute_href()


async def download_file(
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
    if config is None:
        config = Config()
    clients_ = Clients(config, clients=clients)
    client = await clients_.get_client(href)
    await client.download_href(href, destination)

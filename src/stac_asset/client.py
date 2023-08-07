from __future__ import annotations

import asyncio
import os.path
import warnings
from abc import ABC, abstractmethod
from asyncio import Task
from pathlib import Path
from types import TracebackType
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

import aiofiles
import pystac.utils
from pystac import Asset, Item, ItemCollection
from yarl import URL

from .errors import (
    AssetDownloadError,
    AssetOverwriteError,
    CantIncludeAndExclude,
    DownloadError,
    DownloadWarning,
)
from .strategy import FileNameStrategy
from .types import PathLikeObject

T = TypeVar("T", bound="Client")


class Client(ABC):
    """An abstract base class for all clients."""

    @classmethod
    async def default(cls: Type[T]) -> T:
        """Creates the default version of this client.

        ``__init__`` isn't enough because some clients need to do asynchronous
        actions during setup.

        Returns:
            T: The default version of this Client
        """
        return cls()

    @abstractmethod
    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        """Opens a url and yields an iterator over its bytes.

        This is the core method that all clients must implement.

        Args:
            url: The input url

        Yields:
            AsyncIterator[bytes]: An iterator over chunks of the read file
        """
        # https://github.com/python/mypy/issues/5070
        if False:  # pragma: no cover
            yield

    async def open_href(self, href: str) -> AsyncIterator[bytes]:
        """Opens a href and yields an iterator over its bytes.

        Args:
            href: The input href

        Yields:
            AsyncIterator[bytes]: An iterator over chunks of the read file
        """
        async for chunk in self.open_url(URL(href)):
            yield chunk

    async def download_href(
        self, href: str, path: PathLikeObject, clean: bool = True
    ) -> None:
        """Downloads a file to the local filesystem.

        Args:
            href: The input href
            path: The output file path
            clean: If an error occurs, delete the output file if it exists
        """
        try:
            async with aiofiles.open(path, mode="wb") as f:
                async for chunk in self.open_href(href):
                    await f.write(chunk)
        except Exception as err:
            path_as_path = Path(path)
            if clean and path_as_path.exists():
                try:
                    path_as_path.unlink()
                except Exception:
                    pass
            raise err

    async def download_asset(self, key: str, asset: Asset, path: Path) -> None:
        """Downloads an asset.

        Args:
            key: The asset key
            asset: The asset
            path: The path to which the asset will be downloaded

        Raises:
            AssetDownloadError: If any exception is raised during the
                download, it is wrapped in an :py:class:`AssetDownloadError`
        """
        href = asset.get_absolute_href()
        if href is None:
            raise AssetDownloadError(
                key,
                asset,
                ValueError(
                    f"asset '{key}' does not have an absolute href: {asset.href}"
                ),
            )
        try:
            await self.download_href(href, path)
        except Exception as e:
            raise AssetDownloadError(key, asset, e)

    async def download_item(
        self,
        item: Item,
        directory: PathLikeObject,
        *,
        make_directory: bool = False,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        item_file_name: Optional[str] = "item.json",
        include_self_link: bool = True,
        asset_file_name_strategy: FileNameStrategy = FileNameStrategy.FILE_NAME,
        warn_on_download_error: bool = False,
    ) -> Item:
        """Downloads an item and all of its assets to the given directory.

        Args:
            item: The item to download
            directory: The root location of the downloaded files
            make_directory: If true and the directory doesn't exist, create the
                output directory before downloading
            include: Asset keys to download. If not provided, all asset keys
                will be downloaded.
            exclude: Asset keys to not download. If not provided, all asset keys
                will be downloaded.
            item_file_name: The name of the item file. If not provided, the item
                will not be written to the filesystem (only the assets will be
                downloaded).
            include_self_link: Whether to include a self link on the item.
                Unused if ``item_file_name=None``.
            asset_file_name_strategy: The :py:class:`FileNameStrategy` to use
                for naming asset files
            warn_on_download_error: Instead of raising any errors encountered
                while downloading, warn and delete the asset from the item

        Returns:
            Item: The :py:class:`~pystac.Item`, with updated asset hrefs

        Raises:
            CantIncludeAndExclude: Raised if both include and exclude are not None.
        """
        if include is not None and exclude is not None:
            raise CantIncludeAndExclude()

        directory_as_path = Path(directory)
        if not directory_as_path.exists():
            if make_directory:
                directory_as_path.mkdir()
            else:
                raise FileNotFoundError(f"output directory does not exist: {directory}")

        if item_file_name:
            item_path = directory_as_path / item_file_name
        else:
            item_path = None

        tasks: List[Task[Any]] = list()
        file_names: Dict[str, str] = dict()
        item.make_asset_hrefs_absolute()
        for key, asset in (
            (k, a)
            for k, a in item.assets.items()
            if (include is None or k in include)
            and (exclude is None or k not in exclude)
        ):
            # TODO strategy should be auto-guessable
            if asset_file_name_strategy == FileNameStrategy.FILE_NAME:
                file_name = os.path.basename(URL(asset.href).path)
            elif asset_file_name_strategy == FileNameStrategy.KEY:
                file_name = key + Path(asset.href).suffix
            path = directory_as_path / file_name
            if file_name in file_names:
                for task in tasks:
                    task.cancel()
                raise AssetOverwriteError(list(file_names.values()))
            else:
                file_names[file_name] = str(path)

            tasks.append(
                asyncio.create_task(self.download_asset(key, asset.clone(), path))
            )
            if item_path:
                item.assets[key].href = pystac.utils.make_relative_href(
                    str(path), str(item_path)
                )
            else:
                item.assets[key].href = str(path.absolute())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        exceptions = list()
        for result in results:
            if isinstance(result, Exception):
                exceptions.append(result)
        if exceptions:
            if warn_on_download_error:
                for exception in exceptions:
                    warnings.warn(str(exception), DownloadWarning)
                    if isinstance(exception, AssetDownloadError):
                        del item.assets[exception.key]
            else:
                raise DownloadError(exceptions)

        new_links = list()
        for link in item.links:
            link_href = link.get_href(transform_href=False)
            if link_href and not pystac.utils.is_absolute_href(link_href):
                link.target = pystac.utils.make_absolute_href(link.href, item.self_href)
                new_links.append(link)
        item.links = new_links

        if item_path:
            item.set_self_href(str(item_path))
            item.save_object(include_self_link=include_self_link)
        else:
            item.set_self_href(None)

        return item

    async def download_item_collection(
        self,
        item_collection: ItemCollection,
        directory: PathLikeObject,
        *,
        make_directory: bool = False,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        item_collection_file_name: Optional[str] = "item-collection.json",
        asset_file_name_strategy: FileNameStrategy = FileNameStrategy.FILE_NAME,
        warn_on_download_error: bool = False,
    ) -> ItemCollection:
        """Downloads an item collection and all of its assets to the given directory.

        Args:
            item_collection: The item collection to download
            directory: The root location of the downloaded files
            make_directory: If true and and the directory does not exist, create
                the output directory before downloading
            include: Asset keys to download. If not provided, all asset keys
                will be downloaded.
            exclude: Asset keys to not download. If not provided, all asset keys
                will be downloaded.
            item_collection_file_name: The name of the item collection file in the
                directory. If not provided, the item collection will not be
                written to the filesystem (only the assets will be downloaded).
            asset_file_name_strategy: The :py:class:`FileNameStrategy` to use
                for naming asset files
            warn_on_download_error: Instead of raising any errors encountered
                while downloading, warn and delete the asset from the item

        Returns:
            ItemCollection: The :py:class:`~pystac.ItemCollection`, with the
                updated asset hrefs

        Raises:
            CantIncludeAndExclude: Raised if both include and exclude are not None.
        """
        directory_as_path = Path(directory)
        if not directory_as_path.exists():
            if make_directory:
                directory_as_path.mkdir()
            else:
                raise FileNotFoundError(f"output directory does not exist: {directory}")
            directory_as_path.mkdir(exist_ok=True)
        tasks: List[Task[Any]] = list()
        for item in item_collection.items:
            # TODO what happens if items share ids?
            item_directory = directory_as_path / item.id
            tasks.append(
                asyncio.create_task(
                    self.download_item(
                        item=item,
                        directory=item_directory,
                        make_directory=True,
                        include=include,
                        exclude=exclude,
                        item_file_name=None,
                        asset_file_name_strategy=asset_file_name_strategy,
                        warn_on_download_error=warn_on_download_error,
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
        if item_collection_file_name:
            item_collection.save_object(
                dest_href=str(directory_as_path / item_collection_file_name)
            )
        return item_collection

    async def __aenter__(self) -> Client:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        return None

from __future__ import annotations

import asyncio
import os.path
import warnings
from asyncio import Queue
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, Union

import pystac.utils
from pystac import Asset, Collection, Item, STACError
from yarl import URL

from .client import Client
from .config import Config
from .errors import AssetOverwriteError, DownloadError, DownloadWarning
from .filesystem_client import FilesystemClient
from .http_client import HttpClient
from .planetary_computer_client import PlanetaryComputerClient
from .s3_client import S3Client
from .strategy import DownloadStrategy, FileNameStrategy

# Needed until we drop Python 3.8
if TYPE_CHECKING:
    AnyQueue = Queue[Any]
else:
    AnyQueue = Queue


class WrappedError:
    download: Download
    error: Exception

    def __init__(self, download: Download, error: Exception) -> None:
        self.download = download
        self.error = error


@dataclass
class Download:
    owner: Union[Item, Collection]
    key: str
    asset: Asset
    path: Path
    client: Client
    overwrite: bool

    async def download(
        self, make_directory: bool, clean: bool, queue: Optional[AnyQueue]
    ) -> Union[Download, WrappedError]:
        if not self.overwrite and not os.path.exists(self.path):
            try:
                await self.client.download_asset(
                    self.key, self.asset, self.path, make_directory, clean, queue
                )
            except Exception as error:
                return WrappedError(self, error)
        self.asset.href = str(self.path)
        return self


class Downloads:
    clients: Dict[Type[Client], Client]
    config: Config
    downloads: List[Download]

    def __init__(self, config: Config) -> None:
        config.validate()
        self.config = config
        self.downloads = list()
        self.clients = dict()

    async def add(
        self, stac_object: Union[Item, Collection], root: Path, file_name: Optional[str]
    ) -> None:
        links = list()
        for link in stac_object.links:
            absolute_href = link.get_absolute_href()
            if absolute_href:
                link.target = absolute_href
                links.append(link)
        stac_object.links = links
        # Will fail if the stac object doesn't have a self href and there's
        # relative asset hrefs
        stac_object = make_asset_hrefs_absolute(stac_object)

        if file_name:
            item_path = Path(root) / file_name
            stac_object.set_self_href(str(item_path))
        else:
            item_path = None
            stac_object.set_self_href(item_path)

        asset_file_names: Set[str] = set()
        for key, asset in (
            (k, a)
            for k, a in stac_object.assets.items()
            if (not self.config.include or k in self.config.include)
            and (not self.config.exclude or k not in self.config.exclude)
        ):
            if self.config.asset_file_name_strategy == FileNameStrategy.FILE_NAME:
                asset_file_name = os.path.basename(URL(asset.href).path)
            elif self.config.asset_file_name_strategy == FileNameStrategy.KEY:
                asset_file_name = key + Path(asset.href).suffix

            if asset_file_name in asset_file_names:
                raise AssetOverwriteError(list(asset_file_names))
            else:
                asset_file_names.add(asset_file_name)

            client_class = guess_client_class(asset, self.config)
            if client_class in self.clients:
                client = self.clients[client_class]
            else:
                client = await client_class.from_config(self.config)
                self.clients[client_class] = client

            self.downloads.append(
                Download(
                    owner=stac_object,
                    key=key,
                    asset=asset,
                    path=root / asset_file_name,
                    client=client,
                    overwrite=self.config.overwrite,
                )
            )

    async def download(self, queue: Optional[AnyQueue]) -> None:
        tasks = set()
        for download in self.downloads:
            tasks.add(
                asyncio.create_task(
                    download.download(
                        make_directory=self.config.make_directory,
                        clean=self.config.clean,
                        queue=queue,
                    )
                )
            )
        results = await asyncio.gather(*tasks)

        exceptions = set()
        for result in results:
            if isinstance(result, WrappedError):
                if self.config.download_strategy == DownloadStrategy.ERROR:
                    exceptions.add(result.error)
                else:
                    if self.config.download_strategy == DownloadStrategy.DELETE:
                        del result.download.owner.assets[result.download.key]
                    warnings.warn(str(result.error), DownloadWarning)
        if exceptions:
            raise DownloadError(list(exceptions))

    async def __aenter__(self) -> Downloads:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        for client in self.clients.values():
            await client.close()


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


def make_asset_hrefs_absolute(
    stac_object: Union[Item, Collection]
) -> Union[Item, Collection]:
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

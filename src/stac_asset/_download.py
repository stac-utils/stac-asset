from __future__ import annotations

import asyncio
import os.path
import warnings
from asyncio import Queue
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, Union

from pystac import Asset, Collection, Item, STACObject
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


@dataclass
class Download:
    owner: Union[Item, Collection]
    key: str
    asset: Asset
    path: Path
    client: Client

    async def download(
        self, make_directory: bool, clean: bool, queue: Optional[AnyQueue]
    ) -> Union[Download, WrappedError]:
        try:
            self.asset = await self.client.download_asset(
                self.key, self.asset, self.path, make_directory, clean, queue
            )
        except Exception as error:
            return WrappedError(self, error)
        if "alternate" not in self.asset.extra_fields:
            if not has_alternate_assets_extension(self.owner):
                self.owner.stac_extensions.append(
                    "https://stac-extensions.github.io/alternate-assets/v1.1.0/schema.json"
                )
            self.asset.extra_fields["alternate"] = {}
        self.asset.extra_fields["alternate"]["from"] = {"href": self.asset.href}
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

    async def add(self, stac_object: Union[Item, Collection], root: Path) -> None:
        file_names: Set[str] = set()

        for key, asset in (
            (k, a)
            for k, a in stac_object.assets.items()
            if (not self.config.include or k in self.config.include)
            and (not self.config.exclude or k not in self.config.exclude)
        ):
            if self.config.asset_file_name_strategy == FileNameStrategy.FILE_NAME:
                file_name = os.path.basename(URL(asset.href).path)
            elif self.config.asset_file_name_strategy == FileNameStrategy.KEY:
                file_name = key + Path(asset.href).suffix

            if file_name in file_names:
                raise AssetOverwriteError(list(file_names))
            else:
                file_names.add(file_name)

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
                    path=root / file_name,
                    client=client,
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
                    asset.extra_fields["alternate"]["original"] = {"href": href}
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


def has_alternate_assets_extension(stac_object: STACObject) -> bool:
    return any(
        extension.startswith("https://stac-extensions.github.io/alternate-assets")
        for extension in stac_object.stac_extensions
    )


class WrappedError:
    download: Download
    error: Exception

    def __init__(self, download: Download, error: Exception) -> None:
        self.download = download
        self.error = error

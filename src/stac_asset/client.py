from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from types import TracebackType
from typing import AsyncIterator, Optional, Type, TypeVar

import aiofiles
from pystac import Asset
from yarl import URL

from .config import Config
from .types import PathLikeObject

T = TypeVar("T", bound="Client")


class Client(ABC):
    """An abstract base class for all clients."""

    @classmethod
    async def from_config(cls: Type[T], config: Config) -> T:
        """Creates a client using the provided configuration.

        Needed because some client setups require async operations.

        Returns:
            T: A new client Client
        """
        return cls()

    def __init__(self) -> None:
        pass

    @abstractmethod
    async def open_url(
        self, url: URL, content_type: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Opens a url and yields an iterator over its bytes.

        This is the core method that all clients must implement.

        Args:
            url: The input url
            content_type: The expected content type, to be checked by the client
                implementations

        Yields:
            AsyncIterator[bytes]: An iterator over chunks of the read file
        """
        # https://github.com/python/mypy/issues/5070
        if False:  # pragma: no cover
            yield

    async def open_href(
        self, href: str, content_type: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Opens a href and yields an iterator over its bytes.

        Args:
            href: The input href
            content_type: The expected content type

        Yields:
            AsyncIterator[bytes]: An iterator over chunks of the read file
        """
        async for chunk in self.open_url(URL(href), content_type=content_type):
            yield chunk

    async def download_href(
        self,
        href: str,
        path: PathLikeObject,
        clean: bool = True,
        content_type: Optional[str] = None,
    ) -> None:
        """Downloads a file to the local filesystem.

        Args:
            href: The input href
            path: The output file path
            clean: If an error occurs, delete the output file if it exists
            content_type: The expected content type
        """
        try:
            async with aiofiles.open(path, mode="wb") as f:
                async for chunk in self.open_href(href, content_type=content_type):
                    await f.write(chunk)
        except Exception as err:
            path_as_path = Path(path)
            if clean and path_as_path.exists():
                try:
                    path_as_path.unlink()
                except Exception:
                    pass
            raise err

    async def download_asset(
        self, key: str, asset: Asset, path: Path, clean: bool = True
    ) -> Asset:
        """Downloads an asset.

        Args:
            key: The asset key
            asset: The asset
            clean: If an error occurs, delete the output file if it exists
            path: The path to which the asset will be downloaded

        Returns:
            Asset: The asset with an updated href

        Raises:
            ValueError: Raised if the asset does not have an absolute href
        """
        href = asset.get_absolute_href()
        if href is None:
            raise ValueError(
                f"asset '{key}' does not have an absolute href: {asset.href}"
            )
        await self.download_href(href, path, clean=clean, content_type=asset.media_type)
        asset.href = str(path)
        return asset

    async def close(self) -> None:
        """Close this client."""
        pass

    async def __aenter__(self) -> Client:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        return None

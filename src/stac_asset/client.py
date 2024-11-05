from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Lock, QueueFull
from collections.abc import AsyncIterator
from pathlib import Path
from types import TracebackType
from typing import TypeVar

import aiofiles
from yarl import URL

from .config import Config
from .messages import (
    WriteChunk,
)
from .types import MessageQueue, PathLikeObject

T = TypeVar("T", bound="Client")


class Client(ABC):
    """An abstract base class for all clients."""

    name: str
    """The name of this client."""

    @classmethod
    async def from_config(cls: type[T], config: Config) -> T:
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
        self,
        url: URL,
        content_type: str | None = None,
        messages: MessageQueue | None = None,
        stream: bool | None = None,
    ) -> AsyncIterator[bytes]:
        """Opens a url and yields an iterator over its bytes.

        This is the core method that all clients must implement.

        Args:
            url: The input url
            content_type: The expected content type, to be checked by the client
                implementations
            messages: An optional queue to use for progress reporting
            stream: If enabled, it iterates over the bytes of the response;
                otherwise, it reads the entire file into memory

        Yields:
            AsyncIterator[bytes]: An iterator over chunks of the read file
        """
        # https://github.com/python/mypy/issues/5070
        if False:  # pragma: no cover
            yield

    async def open_href(
        self,
        href: str,
        content_type: str | None = None,
        messages: MessageQueue | None = None,
        stream: bool | None = None,
    ) -> AsyncIterator[bytes]:
        """Opens a href and yields an iterator over its bytes.

        Args:
            href: The input href
            content_type: The expected content type
            messages: An optional queue to use for progress reporting
            stream: If enabled, it iterates over the bytes of the response;
                otherwise, it reads the entire file into memory

        Yields:
            AsyncIterator[bytes]: An iterator over chunks of the read file
        """
        async for chunk in self.open_url(
            URL(href), content_type=content_type, messages=messages, stream=stream
        ):
            yield chunk

    async def download_href(
        self,
        href: str,
        path: PathLikeObject,
        clean: bool = True,
        content_type: str | None = None,
        messages: MessageQueue | None = None,
        stream: bool | None = None,
    ) -> None:
        """Downloads a file to the local filesystem.

        Args:
            href: The input href
            path: The output file path
            clean: If an error occurs, delete the output file if it exists
            content_type: The expected content type
            messages: An optional queue to use for progress reporting
            stream: If enabled, it iterates over the bytes of the response;
                otherwise, it reads the entire file into memory
        """
        try:
            async with aiofiles.open(path, mode="wb") as f:
                async for chunk in self.open_href(
                    href, content_type=content_type, messages=messages, stream=stream
                ):
                    await f.write(chunk)
                    if messages:
                        try:
                            messages.put_nowait(
                                WriteChunk(href=href, path=Path(path), size=len(chunk))
                            )
                        except QueueFull:
                            pass

        except Exception as err:
            path_as_path = Path(path)
            if clean and path_as_path.exists():
                try:
                    path_as_path.unlink()
                except Exception:
                    pass
            raise err

    async def href_exists(self, href: str) -> bool:
        """Returns true if the href exists.

        The default implementation naïvely opens the href and reads one chunk.
        Clients may implement specialized behavior.

        Args:
            href: The href to open

        Returns:
            bool: Whether the href exists
        """
        try:
            await self.assert_href_exists(href)
        except Exception:
            return False
        else:
            return True

    async def assert_href_exists(self, href: str) -> None:
        """Asserts that a href exists.

        The default implementation naïvely opens the href and reads one chunk.
        Clients may implement specialized behavior.

        Args:
            href: The href to open

        Raises:
            Exception: The underlying error when trying to open the file.
        """
        async for _ in self.open_href(href):
            break

    async def close(self) -> None:
        """Close this client."""
        pass

    async def __aenter__(self) -> Client:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return None


class Clients:
    """An async-safe cache of clients."""

    lock: Lock
    clients: dict[str, Client]
    config: Config

    def __init__(self, config: Config, clients: list[Client] | None = None) -> None:
        self.lock = Lock()
        self.clients = dict()
        if clients:
            # TODO check for duplicate types in clients list
            for client in clients:
                self.clients[client.name] = client
        self.config = config

    async def get_client(self, href: str) -> Client:
        """Gets a client for the provided href.

        Args:
            href: The file href to download

        Returns:
            Client: An instance of that client.
        """
        # TODO allow dynamic registration of new clients, e.g. via a plugin mechanism

        from .earthdata_client import EarthdataClient
        from .filesystem_client import FilesystemClient
        from .http_client import HttpClient
        from .planetary_computer_client import PlanetaryComputerClient
        from .s3_client import S3Client

        url = URL(href)
        if self.config.client_override:
            client_class: type[Client] = _get_client_class_by_name(
                self.config.client_override
            )
        elif not url.host:
            client_class = FilesystemClient
        elif url.scheme == "s3":
            client_class = S3Client
        elif url.host.endswith("blob.core.windows.net"):
            client_class = PlanetaryComputerClient
        elif url.scheme == "https" and "earthdata" in url.host:
            client_class = EarthdataClient
        elif url.scheme == "http" or url.scheme == "https":
            client_class = HttpClient
        else:
            raise ValueError(f"could not guess client class for href: {href}")

        async with self.lock:
            if client_class.name in self.clients:
                return self.clients[client_class.name]
            else:
                client = await client_class.from_config(self.config)
                self.clients[client_class.name] = client
                return client

    async def close_all(self) -> None:
        """Close all clients."""
        async with self.lock:
            for client in self.clients.values():
                await client.close()


def _get_client_class_by_name(name: str) -> type[Client]:
    for client_class in get_client_classes():
        if client_class.name == name:
            return client_class
    raise ValueError(f"no client with name: {name}")


def get_client_classes() -> list[type[Client]]:
    """Returns a list of all known subclasses of Client."""

    # https://stackoverflow.com/questions/3862310/how-to-find-all-the-subclasses-of-a-class-given-its-name
    def all_subclasses(cls: type[Client]) -> set[type[Client]]:
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in all_subclasses(c)]
        )

    return list(all_subclasses(Client))  # type: ignore

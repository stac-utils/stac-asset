from __future__ import annotations

import os.path
from collections.abc import AsyncIterator
from types import TracebackType

import aiofiles
from yarl import URL

from .client import Client
from .messages import OpenUrl
from .types import MessageQueue


class FilesystemClient(Client):
    """A simple client for moving files around on the filesystem.

    Mostly used for testing, but could be useful in some real-world cases.
    """

    name = "filesystem"

    async def open_url(
        self,
        url: URL,
        content_type: str | None = None,
        messages: MessageQueue | None = None,
        stream: bool | None = None,
    ) -> AsyncIterator[bytes]:
        """Iterates over data from a local url.

        Args:
            url: The url to read bytes from
            content_type: The expected content type. Ignored by this client,
                because filesystems don't have content types.
            messages: An optional queue to use for progress reporting
            stream: If enabled, it iterates over the bytes of the file;
                otherwise, it reads the entire file into memory

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes.

        Raises:
            ValueError: Raised if the url has a scheme. This behavior will
                change if/when we support Windows paths.
        """
        if stream is None:
            stream = False
        if url.scheme:
            raise ValueError(
                "cannot read a file with the filesystem client if it has a url scheme: "
                + str(url)
            )
        if messages:
            await messages.put(OpenUrl(size=os.path.getsize(url.path), url=url))
        async with aiofiles.open(url.path, "rb") as f:
            if stream:
                async for chunk in f:
                    yield chunk
            else:
                content = await f.read()
                yield content

    async def assert_href_exists(self, href: str) -> None:
        """Asserts that an href exists."""
        url = URL(href)
        if not os.path.exists(url.path):
            raise ValueError(f"href does not exist on the filesystem: {href}")

    async def __aenter__(self) -> FilesystemClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return None

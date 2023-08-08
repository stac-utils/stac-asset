from __future__ import annotations

import os.path
from asyncio import Queue
from types import TracebackType
from typing import Any, AsyncIterator, Optional, Type

import aiofiles
from yarl import URL

from .client import Client
from .messages import OpenUrl


class FilesystemClient(Client):
    """A simple client for moving files around on the filesystem.

    Mostly used for testing, but could be useful in some real-world cases.
    """

    async def open_url(
        self,
        url: URL,
        content_type: Optional[str] = None,
        queue: Optional[Queue[Any]] = None,
    ) -> AsyncIterator[bytes]:
        """Iterates over data from a local url.

        Args:
            url: The url to read bytes from
            content_type: The expected content type. Ignored by this client,
                because filesystems don't have content types.
            queue: An optional queue to use for progress reporting

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes.

        Raises:
            ValueError: Raised if the url has a scheme. This behavior will
                change if/when we support Windows paths.
        """
        if url.scheme:
            raise ValueError(
                "cannot read a file with the filesystem client if it has a url scheme: "
                + str(url)
            )
        if queue:
            await queue.put(OpenUrl(size=os.path.getsize(url.path), url=url))
        async with aiofiles.open(url.path, "rb") as f:
            async for chunk in f:
                yield chunk

    async def __aenter__(self) -> FilesystemClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        return None

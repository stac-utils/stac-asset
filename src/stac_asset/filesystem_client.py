from typing import AsyncIterator

import aiofiles
from yarl import URL

from .client import Client


class FilesystemClient(Client):
    """A simple client for moving files around on the filesystem.

    Mostly used for testing, but could be useful in some real-world cases.
    """

    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        if url.scheme:
            raise ValueError(
                "cannot read a file with the filesystem client if it has a url scheme: "
                + str(url)
            )
        async with aiofiles.open(url.path, "rb") as f:
            async for chunk in f:
                yield chunk

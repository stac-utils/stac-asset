from typing import AsyncIterator

import aiofiles
from yarl import URL

from .client import Client


class FilesystemClient(Client):
    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        if url.scheme:
            raise ValueError(
                "cannot read a file with the filesystem client if it has a url scheme: "
                + str(url)
            )
        async with aiofiles.open(url.path, "rb") as f:
            async for chunk in f:
                yield chunk

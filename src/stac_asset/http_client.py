from typing import AsyncIterator, Optional

from httpx import AsyncClient

from .client import Client


class HttpClient(Client):
    client: AsyncClient

    def __init__(self, client: Optional[AsyncClient] = None) -> None:
        super().__init__()
        if client is None:
            self.client = AsyncClient()
        else:
            self.client = client

    async def open_href(self, href: str) -> AsyncIterator[bytes]:
        async with self.client.stream("GET", href) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

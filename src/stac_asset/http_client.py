from typing import AsyncIterator, TypeVar

from aiohttp import ClientSession
from yarl import URL

from .client import Client

T = TypeVar("T", bound="HttpClient")


class HttpClient(Client):
    session: ClientSession

    @classmethod
    async def default(cls: type[T]) -> T:
        session = ClientSession()
        return cls(session)

    def __init__(self, session: ClientSession) -> None:
        super().__init__()
        self.session = session

    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        async with self.session.get(url) as response:
            response.raise_for_status()
            async for chunk, _ in response.content.iter_chunks():
                yield chunk

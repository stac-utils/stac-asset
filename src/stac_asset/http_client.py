from typing import AsyncIterator, TypeVar

from aiohttp import ClientSession
from yarl import URL

from .client import Client

T = TypeVar("T", bound="HttpClient")


class HttpClient(Client):
    """A simple client for making HTTP requests.

    By default, doesn't do any authentication.
    Configure the session to customize its behavior.
    """

    session: ClientSession
    """A atiohttp session that will be used for all requests."""

    @classmethod
    async def default(cls: type[T]) -> T:
        """Creates the default http client with a vanilla session object."""
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

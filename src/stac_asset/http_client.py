from __future__ import annotations

from types import TracebackType
from typing import AsyncIterator, Optional, Type, TypeVar

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
    async def default(cls: Type[T]) -> T:
        """Creates the default http client with a vanilla session object."""
        session = ClientSession()
        return cls(session)

    def __init__(self, session: ClientSession) -> None:
        super().__init__()
        self.session = session

    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        """Opens a url with this client's session and iterates over its bytes.

        Args:
            url: The url to open

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            :py:class:`aiohttp.ClientResponseError`: Raised if the response is not OK
        """
        async with self.session.get(url, allow_redirects=True) as response:
            response.raise_for_status()
            async for chunk, _ in response.content.iter_chunks():
                yield chunk

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self.session.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

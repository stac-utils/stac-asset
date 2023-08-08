from __future__ import annotations

from asyncio import Queue
from types import TracebackType
from typing import Any, AsyncIterator, Optional, Type, TypeVar

from aiohttp import ClientSession
from yarl import URL

from . import validate
from .client import Client
from .config import Config
from .messages import OpenUrl

T = TypeVar("T", bound="HttpClient")


class HttpClient(Client):
    """A simple client for making HTTP requests.

    By default, doesn't do any authentication.
    Configure the session to customize its behavior.
    """

    session: ClientSession
    """A atiohttp session that will be used for all requests."""

    @classmethod
    async def from_config(cls: Type[T], config: Config) -> T:
        """Creates the default http client with a vanilla session object."""
        # TODO add basic auth
        session = ClientSession()
        return cls(session)

    def __init__(self, session: ClientSession, check_content_type: bool = True) -> None:
        super().__init__()
        self.session = session
        self.check_content_type = check_content_type

    async def open_url(
        self,
        url: URL,
        content_type: Optional[str] = None,
        queue: Optional[Queue[Any]] = None,
    ) -> AsyncIterator[bytes]:
        """Opens a url with this client's session and iterates over its bytes.

        Args:
            url: The url to open
            content_type: The expected content type
            queue: An optional queue to use for progress reporting

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            :py:class:`aiohttp.ClientResponseError`: Raised if the response is not OK
        """
        async with self.session.get(url, allow_redirects=True) as response:
            response.raise_for_status()
            if self.check_content_type and content_type:
                validate.content_type(
                    actual=response.content_type, expected=content_type
                )
            if queue:
                await queue.put(OpenUrl(url=url, size=response.content_length))
            async for chunk, _ in response.content.iter_chunks():
                yield chunk

    async def close(self) -> None:
        """Close this http client.

        Closes the underlying session.
        """
        await self.session.close()

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

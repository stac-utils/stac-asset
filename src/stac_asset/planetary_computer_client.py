from __future__ import annotations

import datetime
from asyncio import Lock
from datetime import timezone
from types import TracebackType
from typing import Any, AsyncIterator, Dict, Optional, Type

from aiohttp import ClientSession
from yarl import URL

from .http_client import HttpClient

DEFAULT_SAS_TOKEN_ENDPOINT = "https://planetarycomputer.microsoft.com/api/sas/v1/token"


class _Token:
    expiry: datetime.datetime
    token: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> _Token:
        try:
            expiry = datetime.datetime.fromisoformat(data["msft:expiry"])
        except KeyError:
            raise ValueError(f"missing 'msft:expiry' key in dict: {data}")

        try:
            token = data["token"]
        except KeyError:
            raise ValueError(f"missing 'token' key in dict: {data}")

        return cls(expiry=expiry, token=token)

    def __init__(self, expiry: datetime.datetime, token: str) -> None:
        self.expiry = expiry
        self.token = token

    def ttl(self) -> float:
        return (self.expiry - datetime.datetime.now(timezone.utc)).total_seconds()

    def __str__(self) -> str:
        return self.token


class PlanetaryComputerClient(HttpClient):
    """Open and download assets from Microsoft's Planetary Computer.

    Heavily cribbed from
    https://github.com/microsoft/planetary-computer-sdk-for-python/blob/main/planetary_computer/sas.py,
    thanks Tom Augspurger!
    """

    _cache: Dict[URL, _Token]
    _cache_lock: Lock
    token_request_url: URL

    def __init__(
        self,
        session: ClientSession,
        sas_token_endpoint: str = DEFAULT_SAS_TOKEN_ENDPOINT,
    ) -> None:
        super().__init__(session)
        self._cache = dict()
        self._cache_lock = Lock()
        self.sas_token_endpoint = URL(sas_token_endpoint)

    async def open_url(
        self, url: URL, content_type: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Opens a url and iterates over its bytes.

        Includes functionality to sign the url with a SAS token fetched from
        this client's ``sas_token_endpoint``. Tokens are cached on a per-client
        basis to prevent a large number of requests when fetching many assets.

        Not every URL is modified with a SAS token. We only modify the url if:

        - The url is in Azure blob storage
        - The url is not in the public thumbnail storage account
        - The url hasn't already signed (we check this by seeing if the url has
            SAS-like query parameters)

        Args:
            url: The url to open
            content_type: The expected content type

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes
        """
        if (
            url.host is not None
            and url.host.endswith(".blob.core.windows.net")
            and not url.host == "ai4edatasetspublicassets.blob.core.windows.net"
            and not set(url.query) & {"st", "se", "sp"}
        ):
            url = await self._sign(url)
        async for chunk in super().open_url(url, content_type=content_type):
            yield chunk

    async def _sign(self, url: URL) -> URL:
        assert url.host
        account_name = url.host.split(".")[0]
        container_name = url.path.split("/", 2)[1]
        token = await self._get_token(account_name, container_name)
        return URL(str(url.with_query(None)) + "?" + token, encoded=False)

    async def _get_token(self, account_name: str, container_name: str) -> str:
        url = self.sas_token_endpoint.joinpath(account_name, container_name)
        async with self._cache_lock:
            token = self._cache.get(url)
            if token is None or token.ttl() < 60:
                response = await self.session.get(url)
                response.raise_for_status()
                token = _Token.from_dict(await response.json())
                self._cache[url] = token
        return str(token)

    async def __aenter__(self) -> PlanetaryComputerClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

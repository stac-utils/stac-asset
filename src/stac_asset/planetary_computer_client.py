"""Open and download assets from Microsoft's Planetary Computer.

Heavily cribbed from
https://github.com/microsoft/planetary-computer-sdk-for-python/blob/main/planetary_computer/sas.py,
thanks Tom Augspurger!
"""

from __future__ import annotations

import datetime
from datetime import timezone
from typing import Any, AsyncIterator, Dict

from aiohttp import ClientSession
from yarl import URL

from .http_client import HttpClient

DEFAULT_SAS_TOKEN_ENDPOINT = "https://planetarycomputer.microsoft.com/api/sas/v1/token"


class _Token:
    expiry: datetime.datetime
    token: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _Token:
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
    cache: Dict[URL, _Token]
    token_request_url: URL

    def __init__(
        self,
        session: ClientSession,
        sas_token_endpoint: str = DEFAULT_SAS_TOKEN_ENDPOINT,
    ) -> None:
        super().__init__(session)
        self.cache = dict()
        self.sas_token_endpoint = URL(sas_token_endpoint)

    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        # We only need to modify the url if:
        #
        # - The url is in Azure blob storage
        # - The url is not in the public thumbnail storage account
        # - The url hasn't already signed (we check this by seeing if the url
        #   has SAS-like query parameters)
        if (
            url.host is not None
            and url.host.endswith(".blob.core.windows.net")
            and not url.host == "ai4edatasetspublicassets.blob.core.windows.net"
            and not set(url.query) & {"st", "se", "sp"}
        ):
            url = await self._sign(url)
        async for chunk in super().open_url(url):
            yield chunk

    async def _sign(self, url: URL) -> URL:
        assert url.host
        account_name = url.host.split(".")[0]
        container_name = url.path.split("/", 2)[1]
        token = await self._get_token(account_name, container_name)
        return URL(str(url.with_query(None)) + "?" + token, encoded=False)

    async def _get_token(self, account_name: str, container_name: str) -> str:
        url = self.sas_token_endpoint.joinpath(account_name, container_name)
        token = self.cache.get(url)
        if token is None or token.ttl() < 60:
            response = await self.session.get(url)
            response.raise_for_status()
            token = _Token.from_dict(await response.json())
            self.cache[url] = token
        return str(token)

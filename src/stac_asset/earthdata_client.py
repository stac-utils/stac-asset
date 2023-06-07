from __future__ import annotations

import os
from types import TracebackType
from typing import Optional, Type

from aiohttp import ClientSession

from .http_client import HttpClient


class EarthdataClient(HttpClient):
    """Access data from https://www.earthdata.nasa.gov/."""

    @classmethod
    async def default(cls) -> EarthdataClient:
        """Logs in to Earthdata and returns the default earthdata client.

        Uses a token stored in the ``EARTHDATA_PAT`` environment variable.
        """
        return await cls.login()

    @classmethod
    async def login(cls, token: Optional[str] = None) -> EarthdataClient:
        """Logs in to Earthdata and returns a client.

        If token is not provided, it is read from the ``EARTHDATA_PAT``
        environment variable.

        Args:
            token: The Earthdata bearer token

        Returns:
            EarthdataClient: A client configured to use the bearer token
        """
        if token is None:
            try:
                token = os.environ["EARTHDATA_PAT"]
            except KeyError:
                raise ValueError(
                    "token was not provided, and EARTHDATA_PAT environment variable "
                    "not set"
                )
        session = ClientSession(headers={"Authorization": f"Bearer {token}"})
        return cls(session)

    async def __aenter__(self) -> EarthdataClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self.session.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

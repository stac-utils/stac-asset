from __future__ import annotations

import os
from types import TracebackType
from typing import Optional, Type

from aiohttp import ClientSession

from .config import Config
from .http_client import HttpClient


class EarthdataClient(HttpClient):
    """Access data from https://www.earthdata.nasa.gov/.

    To access data, you'll need a personal access token.

    1. Create a new personal access token by going to
       https://urs.earthdata.nasa.gov/profile and then clicking "Generate Token"
       (you'll need to log in).
    2. Set an environment variable named ``EARTHDATA_PAT`` to your token.
    3. Use :py:meth:`EarthdataClient.from_config()` to create a new client.

    You can also provide your token directly to :py:func:`EarthdataClient.login()`.
    """

    @classmethod
    async def from_config(cls, config: Config) -> EarthdataClient:
        """Logs in to Earthdata and returns the default earthdata client.

        Uses a token stored in the ``EARTHDATA_PAT`` environment variable, if
        the token is not provided in the config.

        Args:
            config: A configuration object.

        Returns:
            EarthdataClient: A logged-in EarthData client.
        """
        return await cls.login(config.earthdata_token)

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
        await self.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

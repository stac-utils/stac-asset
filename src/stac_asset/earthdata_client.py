from __future__ import annotations

import os
from types import TracebackType
from typing import Optional

from aiohttp import ClientSession

from .http_client import HttpClient


class EarthdataClient(HttpClient):
    @classmethod
    async def default(cls) -> EarthdataClient:
        return await cls.login()

    @classmethod
    async def login(cls, token: Optional[str] = None) -> EarthdataClient:
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
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self.session.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

from __future__ import annotations

import json
import os
from types import TracebackType
from typing import Optional, Type

from aiohttp import ClientSession

from .http_client import HttpClient


class UsgsErosClient(HttpClient):
    @classmethod
    async def default(
        cls,
    ) -> UsgsErosClient:
        """Logs in to the USGS EROS system using your environment variables."""
        return await cls.login()

    @classmethod
    async def login(
        cls,
        username: Optional[str] = None,
        pat: Optional[str] = None,
    ) -> UsgsErosClient:
        """Retrieves a token from USGS EROS that will be used for all requests.

        Args:
            username: Your USGS EROS username. Will be read from the
                USGS_EROS_USERNAME environment variable if not provided.
            pat: Your USGS EROS personal access token. Will be read from the
                USGS_EROS_PAT environment variable if not provided.
        """
        if username is None:
            try:
                username = os.environ["USGS_EROS_USERNAME"]
            except KeyError:
                raise ValueError(
                    "USGS_EROS_USERNAME is not set as an environment variable, "
                    "and no username was provided"
                )
        if pat is None:
            try:
                pat = os.environ.get("USGS_EROS_PAT")
            except KeyError:
                raise ValueError(
                    "USGS_EROS_PAT is not set as an environment variable, "
                    "and no personal access token was provided"
                )
        session = ClientSession()
        response = await session.post(
            "https://m2m.cr.usgs.gov/api/api/json/stable/login-token",
            data=json.dumps({"username": username, "token": pat}),
        )
        response.raise_for_status()
        data = await response.json()
        try:
            api_key = data["data"]
        except KeyError:
            raise ValueError(
                f"unexpected response format (expected 'data' key): {json.dumps(data)}"
            )
        return cls(
            session=ClientSession(
                headers={"X-Auth-Token": api_key},
            )
        )

    async def __aenter__(self) -> UsgsErosClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        await self.session.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

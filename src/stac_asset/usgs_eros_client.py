from __future__ import annotations

import json
import os
from typing import Optional

from httpx import AsyncClient

from .http_client import HttpClient


class UsgsErosClient(HttpClient):
    @classmethod
    async def login(
        cls,
        username: Optional[str] = None,
        pat: Optional[str] = None,
        # The USGS download API has redirects in it so it can be nice to follow them.
        follow_redirects: bool = True,
    ) -> UsgsErosClient:
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
        client = AsyncClient()
        response = await client.post(
            "https://m2m.cr.usgs.gov/api/api/json/stable/login-token",
            json={"username": username, "token": pat},
        )
        response.raise_for_status()
        data = response.json()
        try:
            api_key = data["data"]
        except KeyError:
            raise ValueError(
                f"unexpected response format (expected 'data' key): {json.dumps(data)}"
            )
        return cls(
            client=AsyncClient(
                headers={"X-Auth-Token": api_key}, follow_redirects=follow_redirects
            )
        )

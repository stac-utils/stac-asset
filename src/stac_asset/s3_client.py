from __future__ import annotations

from types import TracebackType
from typing import AsyncIterator, Optional

import aiobotocore.session
from aiobotocore.session import AioSession
from botocore import UNSIGNED
from botocore.config import Config
from yarl import URL

from .client import Client

DEFAULT_REGION_NAME = "us-west-2"


class S3Client(Client):
    session: AioSession
    """The session that will be used for all s3 requests."""

    region_name: str
    """The region that all clients will be rooted in."""

    requester_pays: bool
    """If True, add `--request-payer requester` to all requests."""

    def __init__(
        self, region_name: str = DEFAULT_REGION_NAME, requester_pays: bool = False
    ) -> None:
        super().__init__()
        self.session = aiobotocore.session.get_session()
        self.region_name = region_name
        self.requester_pays = requester_pays

    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        if url.scheme != "s3":
            raise ValueError(f"only s3 urls are allowed: {url}")
        if self.requester_pays:
            config = Config()
        else:
            config = Config(signature_version=UNSIGNED)
        async with self.session.create_client(
            "s3",
            region_name=self.region_name,
            config=config,
        ) as client:
            bucket = url.host
            key = url.path[1:]
            params = {
                "Bucket": bucket,
                "Key": key,
            }
            if self.requester_pays:
                params["RequestPayer"] = "requester"
            response = await client.get_object(**params)
            async for chunk in response["Body"]:
                yield chunk

    async def __aenter__(self) -> S3Client:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        return None

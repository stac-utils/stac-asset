from __future__ import annotations

from types import TracebackType
from typing import AsyncIterator, Optional, Type

import aiobotocore.session
import botocore.config
from aiobotocore.session import AioSession
from botocore import UNSIGNED
from yarl import URL

from . import validate
from .client import Client
from .config import DEFAULT_S3_REGION_NAME, Config


class S3Client(Client):
    """A client for interacting with s3 urls."""

    session: AioSession
    """The session that will be used for all s3 requests."""

    region_name: str
    """The region that all clients will be rooted in."""

    requester_pays: bool
    """If True, add `--request-payer requester` to all requests."""

    @classmethod
    async def from_config(cls, config: Config) -> S3Client:
        """Creates an s3 client from a config.

        Args:
            config: The config object

        Returns:
            S3Client: A new s3 client
        """
        return cls(
            requester_pays=config.s3_requester_pays, region_name=config.s3_region_name
        )

    def __init__(
        self,
        requester_pays: bool = False,
        region_name: str = DEFAULT_S3_REGION_NAME,
    ) -> None:
        super().__init__()
        self.session = aiobotocore.session.get_session()
        self.region_name = region_name
        self.requester_pays = requester_pays

    async def open_url(
        self, url: URL, content_type: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Opens an s3 url and iterates over its bytes.

        Args:
            url: The url to open
            content_type: The expected content type

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            SchemeError: Raised if the url's scheme is not ``s3``
        """
        if self.requester_pays:
            config = botocore.config.Config()
        else:
            config = botocore.config.Config(signature_version=UNSIGNED)
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
            if content_type:
                validate.content_type(response["ContentType"], content_type)
            async for chunk in response["Body"]:
                yield chunk

    async def has_credentials(self) -> bool:
        """Returns true if the sessions has credentials."""
        return await self.session.get_credentials() is not None

    async def __aenter__(self) -> S3Client:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        return None

from __future__ import annotations

from asyncio import Queue
from types import TracebackType
from typing import Any, AsyncIterator, Optional, Type

import aiobotocore.session
import botocore.config
from aiobotocore.session import AioSession
from botocore import UNSIGNED
from yarl import URL

from . import validate
from .client import Client
from .config import (
    DEFAULT_S3_MAX_ATTEMPTS,
    DEFAULT_S3_REGION_NAME,
    DEFAULT_S3_RETRY_MODE,
    Config,
)
from .messages import OpenUrl


class S3Client(Client):
    """A client for interacting with s3 urls."""

    session: AioSession
    """The session that will be used for all s3 requests."""

    region_name: str
    """The region that all clients will be rooted in."""

    requester_pays: bool
    """If True, add `--request-payer requester` to all requests."""

    retry_mode: str
    """The retry mode."""

    max_attempts: int
    """The maximum number of attempts."""

    @classmethod
    async def from_config(cls, config: Config) -> S3Client:
        """Creates an s3 client from a config.

        Args:
            config: The config object

        Returns:
            S3Client: A new s3 client
        """
        return cls(
            requester_pays=config.s3_requester_pays,
            region_name=config.s3_region_name,
            retry_mode=config.s3_retry_mode,
            max_attempts=config.s3_max_attempts,
        )

    def __init__(
        self,
        requester_pays: bool = False,
        region_name: str = DEFAULT_S3_REGION_NAME,
        retry_mode: str = DEFAULT_S3_RETRY_MODE,
        max_attempts: int = DEFAULT_S3_MAX_ATTEMPTS,
    ) -> None:
        super().__init__()
        self.session = aiobotocore.session.get_session()
        self.region_name = region_name
        self.requester_pays = requester_pays
        self.retry_mode = retry_mode
        self.max_attempts = max_attempts

    async def open_url(
        self,
        url: URL,
        content_type: Optional[str] = None,
        queue: Optional[Queue[Any]] = None,
    ) -> AsyncIterator[bytes]:
        """Opens an s3 url and iterates over its bytes.

        Args:
            url: The url to open
            content_type: The expected content type
            queue: An optional queue to use for progress reporting

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            SchemeError: Raised if the url's scheme is not ``s3``
        """
        retries = {
            "max_attempts": self.max_attempts,
            "mode": self.retry_mode,
        }
        if self.requester_pays:
            config = botocore.config.Config(retries=retries)
        else:
            config = botocore.config.Config(signature_version=UNSIGNED, retries=retries)
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
            if queue:
                await queue.put(OpenUrl(url=url, size=response["ContentLength"]))
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

from __future__ import annotations

from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any

import aiobotocore.session
import botocore.config
from aiobotocore.session import AioSession, ClientCreatorContext
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
from .types import MessageQueue


class S3Client(Client):
    """A client for interacting with s3 urls.

    To use the ``requester_pays`` option, you need to configure your AWS
    credentials. See `the AWS documentation
    <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html>`_
    for instructions.
    """

    name = "s3"

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
            endpoint_url=config.s3_endpoint_url,
        )

    def __init__(
        self,
        requester_pays: bool = False,
        region_name: str = DEFAULT_S3_REGION_NAME,
        retry_mode: str = DEFAULT_S3_RETRY_MODE,
        max_attempts: int = DEFAULT_S3_MAX_ATTEMPTS,
        endpoint_url: str | None = None,
    ) -> None:
        super().__init__()

        self.session: AioSession = aiobotocore.session.get_session()
        """The session that will be used for all s3 requests."""

        self.region_name: str = region_name
        """The region that all clients will be rooted in."""

        self.requester_pays: bool = requester_pays
        """If True, enable access to `requester pays buckets
        <https://docs.aws.amazon.com/AmazonS3/latest/userguide/RequesterPaysBuckets.html>`_."""

        self.retry_mode: str = retry_mode
        """The retry mode, one of "adaptive", "legacy", or "standard".

        See `the boto3 docs
        <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html>`_
        for more information on the available modes.
        """

        self.max_attempts: int = max_attempts
        """The maximum number of attempts."""

        self.endpoint_url: str | None = endpoint_url
        """Custom endpoint url for s3."""

    async def open_url(
        self,
        url: URL,
        content_type: str | None = None,
        messages: MessageQueue | None = None,
        stream: bool | None = None,
    ) -> AsyncIterator[bytes]:
        """Opens an s3 url and iterates over its bytes.

        Args:
            url: The url to open
            content_type: The expected content type
            messages: An optional queue to use for progress reporting
            stream: If enabled, it iterates over the bytes of the response;
                otherwise, it reads the entire file into memory

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            SchemeError: Raised if the url's scheme is not ``s3``
        """
        if stream is None:
            stream = True
        async with self._create_client() as client:
            response = await client.get_object(**self._params(url))
            if content_type:
                validate.content_type(response["ContentType"], content_type)
            if messages:
                await messages.put(OpenUrl(url=url, size=response["ContentLength"]))
            if stream:
                async for chunk in response["Body"]:
                    yield chunk
            else:
                content = await response["Body"].read()
                yield content

    async def has_credentials(self) -> bool:
        """Returns true if the sessions has credentials."""
        return await self.session.get_credentials() is not None

    async def assert_href_exists(self, href: str) -> None:
        """Asserts that the href exists.

        Uses ``head_object``
        """
        async with self._create_client() as client:
            await client.head_object(**self._params(URL(href)))

    def _create_client(self) -> ClientCreatorContext:
        retries = {
            "max_attempts": self.max_attempts,
            "mode": self.retry_mode,
        }
        if self.requester_pays:
            config = botocore.config.Config(retries=retries)
        else:
            config = botocore.config.Config(signature_version=UNSIGNED, retries=retries)
        return self.session.create_client(
            "s3",
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
            config=config,
        )

    def _params(self, url: URL) -> dict[str, Any]:
        bucket = url.host
        key = url.path[1:]
        params = {
            "Bucket": bucket,
            "Key": key,
        }
        if self.requester_pays:
            params["RequestPayer"] = "requester"
        return params

    async def __aenter__(self) -> S3Client:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return None

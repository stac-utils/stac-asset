from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import AsyncIterator, Optional, Type

import aiobotocore.session
from aiobotocore.session import AioSession
from botocore import UNSIGNED
from botocore.config import Config
from pystac import Asset
from yarl import URL

from .client import Client
from .errors import AssetDownloadError, SchemeError

DEFAULT_REGION_NAME = "us-west-2"


class S3Client(Client):
    """A client for interacting with s3 urls."""

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
        """Opens an s3 url and iterates over its bytes.

        Args:
            url: The url to open

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            SchemeError: Raised if the url's scheme is not ``s3``
        """
        if url.scheme != "s3":
            raise SchemeError(f"only s3 urls are allowed: {url}")
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

    async def download_asset(self, key: str, asset: Asset, path: Path) -> None:
        """Downloads an asset to a location.

        If the initial download fails with a scheme error, the client looks for
        an alternate href and tries again with that.

        Args:
            key: The asset key
            asset: The asset
            path: The destination path
        """
        try:
            return await super().download_asset(key, asset, path)
        except AssetDownloadError as err:
            if isinstance(err.err, SchemeError):
                maybe_asset = self._asset_with_alternate_href(asset)
                if maybe_asset:
                    return await super().download_asset(key, maybe_asset, path)
            raise err

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

    def _asset_with_alternate_href(self, asset: Asset) -> Optional[Asset]:
        # TODO some of this logic could be refactored out to be more common, but
        # not all (e.g. requester pays)
        alternate = asset.extra_fields.get("alternate")
        if alternate and isinstance(alternate, dict):
            s3 = alternate.get("s3")
            if s3 and isinstance(s3, dict):
                requester_pays = s3.get("storage:requester_pays", False)
                href = s3.get("href")
                platform = s3.get("storage:platform", "AWS")
                if platform == "AWS" and href:
                    if requester_pays and not self.requester_pays:
                        raise ValueError(
                            f"alternate href {href} requires requester pays, but "
                            "requester pays is not enabled on this client"
                        )
                    asset.href = href
                    return asset
        return None

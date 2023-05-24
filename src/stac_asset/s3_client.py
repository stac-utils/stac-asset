from typing import AsyncIterator

import aiobotocore.session
from aiobotocore.session import AioSession
from botocore import UNSIGNED
from botocore.config import Config
from yarl import URL

from .client import Client

DEFAULT_REGION_NAME = "us-west-2"


class S3Client(Client):
    session: AioSession
    region_name: str

    def __init__(self, region_name: str = DEFAULT_REGION_NAME) -> None:
        super().__init__()
        self.session = aiobotocore.session.get_session()
        self.region_name = region_name

    async def open_url(self, url: URL) -> AsyncIterator[bytes]:
        if url.scheme != "s3":
            raise ValueError(f"only s3 urls are allowed: {url}")
        async with self.session.create_client(
            "s3",
            region_name=self.region_name,
            config=Config(signature_version=UNSIGNED),
        ) as client:
            bucket = url.host
            key = url.path[1:]
            response = await client.get_object(Bucket=bucket, Key=key)
            async for chunk in response["Body"]:
                yield chunk

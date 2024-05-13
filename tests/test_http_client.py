import pytest
from stac_asset import Config, HttpClient

pytestmark = [
    pytest.mark.asyncio,
]


@pytest.mark.vcr
async def test_href_exists() -> None:
    async with await HttpClient.from_config(Config()) as client:
        assert await client.href_exists("https://github.com/stac-utils/stac-asset")


async def test_default_http_timeout() -> None:
    async with await HttpClient.from_config(Config(http_client_timeout=42)) as client:
        assert client.session.timeout.total == 42

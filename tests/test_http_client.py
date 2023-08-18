import pytest
from stac_asset import Config, HttpClient

pytestmark = [
    pytest.mark.network_access,
    pytest.mark.asyncio,
]


async def test_href_exists() -> None:
    async with await HttpClient.from_config(Config()) as client:
        assert await client.href_exists("https://github.com/stac-utils/stac-asset")

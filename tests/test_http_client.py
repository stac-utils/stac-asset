import pytest
from stac_asset import Config, HttpClient

pytestmark = [
    pytest.mark.asyncio,
]


@pytest.mark.vcr
async def test_href_exists() -> None:
    async with await HttpClient.from_config(Config()) as client:
        assert await client.href_exists("https://github.com/stac-utils/stac-asset")

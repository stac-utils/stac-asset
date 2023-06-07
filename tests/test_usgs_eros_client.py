import os
from pathlib import Path

import pytest
from stac_asset import UsgsErosClient

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("USGS_EROS_USERNAME") is None
        or os.environ.get("USGS_EROS_PAT") is None,
        reason="USGS_EROS_USERNAME or USGS_EROS_PAT are not set",
    ),
    pytest.mark.network_access,
    pytest.mark.asyncio,
]


@pytest.fixture
def asset_href() -> str:
    return (
        "https://landsatlook.usgs.gov/data/collection02/level-2/standard/oli-tirs/2022/004"
        "/004/LC08_L2SP_004004_20220519_20220525_02_T1/LC08_L2SP_004004_20220519_20220525_02_T1_thumb_small.jpeg"
    )


async def test_download(tmp_path: Path, asset_href: str) -> None:
    async with await UsgsErosClient.login() as client:
        await client.download_href(asset_href, tmp_path / "out.jpg")

    assert os.path.getsize(tmp_path / "out.jpg") == 18517

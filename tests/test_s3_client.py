import os.path
from pathlib import Path

import pytest
from stac_asset import S3Client

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


@pytest.fixture
def href() -> str:
    return "s3://sentinel-cogs/sentinel-s2-l2a-cogs/42/L/TQ/2023/5/S2B_42LTQ_20230524_0_L2A/thumbnail.jpg"


@pytest.fixture
def requester_pays_href() -> str:
    return "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2023/092/068/LC09_L2SP_092068_20230522_20230524_02_T2/LC09_L2SP_092068_20230522_20230524_02_T2_thumb_small.jpeg"


async def test_download(tmp_path: Path, href: str) -> None:
    async with await S3Client.default() as client:
        await client.download_href(href, tmp_path / "out.jpg")
        assert os.path.getsize(tmp_path / "out.jpg") == 6060


async def test_download_requester_pays(
    tmp_path: Path, requester_pays_href: str
) -> None:
    async with S3Client(requester_pays=True) as client:
        await client.download_href(requester_pays_href, tmp_path / "out.jpg")
        assert os.path.getsize(tmp_path / "out.jpg") == 6114

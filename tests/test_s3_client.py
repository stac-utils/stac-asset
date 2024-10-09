import os.path
from pathlib import Path
from typing import cast

import pystac
import pytest
from pystac import Item

import stac_asset
from stac_asset import Config, S3Client

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


@pytest.fixture
def asset_href() -> str:
    return "s3://sentinel-cogs/sentinel-s2-l2a-cogs/42/L/TQ/2023/5/S2B_42LTQ_20230524_0_L2A/thumbnail.jpg"


@pytest.fixture
def requester_pays_asset_href() -> str:
    return "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2023/092/068/LC09_L2SP_092068_20230522_20230524_02_T2/LC09_L2SP_092068_20230522_20230524_02_T2_thumb_small.jpeg"


@pytest.fixture
def requester_pays_item(data_path: Path) -> Item:
    return cast(
        Item,
        pystac.read_file(
            str(data_path / "LC09_L2SP_092068_20230607_20230609_02_T1_SR.json")
        ),
    )


async def test_download(tmp_path: Path, asset_href: str) -> None:
    async with S3Client() as client:
        await client.download_href(asset_href, tmp_path / "out.jpg")

    assert os.path.getsize(tmp_path / "out.jpg") == 6060


async def test_href_exists(asset_href: str) -> None:
    async with S3Client() as client:
        assert await client.href_exists(asset_href)
        assert not await client.href_exists("s3://does-not-exist/not-a-file")


async def test_download_requester_pays_asset(
    tmp_path: Path, requester_pays_asset_href: str
) -> None:
    async with S3Client(requester_pays=True) as client:
        if not await client.has_credentials():
            pytest.skip("aws credentials are invalid or not present")
        await client.download_href(requester_pays_asset_href, tmp_path / "out.jpg")
        assert os.path.getsize(tmp_path / "out.jpg") == 6114


async def test_download_requester_pays_item(
    tmp_path: Path, requester_pays_item: Item
) -> None:
    await stac_asset.download_item(
        requester_pays_item,
        tmp_path,
        config=Config(
            include=["thumbnail"], s3_requester_pays=True, alternate_assets=["s3"]
        ),
    )
    assert (
        os.path.getsize(
            tmp_path / "LC09_L2SP_092068_20230607_20230609_02_T1_thumb_small.jpeg"
        )
        == 19554
    )

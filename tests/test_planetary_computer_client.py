import os.path
from pathlib import Path

import pytest
from stac_asset import PlanetaryComputerClient

pytestmark = [
    pytest.mark.network_access,
    pytest.mark.asyncio,
]


@pytest.fixture
def href() -> str:
    return "https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/48/X/VR/2023/05/24/S2B_MSIL2A_20230524T084609_N0509_R107_T48XVR_20230524T120352.SAFE/GRANULE/L2A_T48XVR_A032451_20230524T084603/QI_DATA/T48XVR_20230524T084609_PVI.tif"


async def test_download(tmp_path: Path, href: str) -> None:
    async with await PlanetaryComputerClient.default() as client:
        await client.download_href(href, tmp_path / "out.tif")
        assert os.path.getsize(tmp_path / "out.tif") == 4096

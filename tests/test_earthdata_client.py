import os.path
from pathlib import Path

import pytest
from stac_asset import Config, EarthdataClient

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("EARTHDATA_PAT") is None,
        reason="EARTHDATA_PAT is not set",
    ),
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


async def test_download_href(tmp_path: Path) -> None:
    href = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MYD11A1.061/MYD11A1.A2023145.h14v17.061.2023146183035/MYD11A1.A2023145.h14v17.061.2023146183035.hdf"
    async with await EarthdataClient.from_config(Config()) as client:
        await client.download_href(href, tmp_path / "out.hdf")
        assert os.path.getsize(tmp_path / "out.hdf") == 197419

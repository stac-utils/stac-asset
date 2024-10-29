import os.path
from pathlib import Path

import pytest

from stac_asset import Config, EarthdataClient
from stac_asset.client import Clients

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("EARTHDATA_PAT") is None,
        reason="EARTHDATA_PAT is not set",
    ),
    pytest.mark.asyncio,
]


@pytest.mark.network_access
async def test_download_href(tmp_path: Path) -> None:
    href = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MYD11A1.061/MYD11A1.A2023145.h14v17.061.2023146183035/MYD11A1.A2023145.h14v17.061.2023146183035.hdf"
    async with await EarthdataClient.from_config(Config()) as client:
        await client.download_href(href, tmp_path / "out.hdf")
        assert os.path.getsize(tmp_path / "out.hdf") == 197419


async def test_get_earthdata_client() -> None:
    href = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD21A1D.061/MOD21A1D.A2020253.h08v05.061.2020346022258/MOD21A1D.A2020253.h08v05.061.2020346022258.hdf"
    clients = Clients(Config())
    assert isinstance(await clients.get_client(href=href), EarthdataClient)

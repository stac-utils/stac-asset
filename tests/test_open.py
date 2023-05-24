# VCR testing blocked by https://github.com/kevin1024/vcrpy/issues/597

import os.path
from pathlib import Path

import pytest
import stac_asset
from pystac import Asset

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


async def test_open_http_href(tmp_path: Path, asset_href: str) -> None:
    with open(tmp_path / "out.jpg", "wb") as f:
        async for chunk in stac_asset.open_href(asset_href):
            f.write(chunk)
    assert os.path.getsize(tmp_path / "out.jpg") == 31367


async def test_open_http_asset(tmp_path: Path, asset_href: str) -> None:
    asset = Asset(href=asset_href)
    with open(tmp_path / "out.jpg", "wb") as f:
        async for chunk in stac_asset.open_asset(asset):
            f.write(chunk)
    assert os.path.getsize(tmp_path / "out.jpg") == 31367

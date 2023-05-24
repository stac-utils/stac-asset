# VCR testing blocked by https://github.com/kevin1024/vcrpy/issues/597

import json
import os.path
from pathlib import Path

import pytest
import stac_asset
from pystac import Asset

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


async def test_download_http_href(tmp_path: Path, asset_href: str) -> None:
    await stac_asset.download_href(asset_href, tmp_path / "out.jpg")
    assert os.path.getsize(tmp_path / "out.jpg") == 31367


async def test_open_http_asset(tmp_path: Path, asset_href: str) -> None:
    asset = Asset(href=asset_href)
    await stac_asset.download_asset(asset, tmp_path)
    assert os.path.getsize(tmp_path / "20201211_223832_CS2.jpg") == 31367

    with open(tmp_path / "asset.json") as f:
        asset = Asset.from_dict(json.load(f))
    assert asset.href == str(Path(tmp_path) / "20201211_223832_CS2.jpg")

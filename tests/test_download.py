import os.path
from pathlib import Path

import pytest
import stac_asset

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


async def test_download_http_href(tmp_path: Path, asset_href: str) -> None:
    await stac_asset.download_href(asset_href, tmp_path / "out.jpg")
    assert os.path.getsize(tmp_path / "out.jpg") == 31367

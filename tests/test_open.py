import os.path
from pathlib import Path

import pytest
import stac_asset

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


async def test_open_http_href(tmp_path: Path, asset_href: str) -> None:
    with open(tmp_path / "out.jpg", "wb") as f:
        async for chunk in stac_asset.open_href(asset_href):
            f.write(chunk)
    assert os.path.getsize(tmp_path / "out.jpg") == 31367

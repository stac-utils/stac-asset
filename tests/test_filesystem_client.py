import os.path
from pathlib import Path

import pytest
from stac_asset import FilesystemClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
def asset_href() -> str:
    return str(Path(__file__).parent / "data" / "20201211_223832_CS2.jpg")


async def test_download(tmp_path: Path, asset_href: str) -> None:
    async with FilesystemClient() as client:
        await client.download_href(asset_href, tmp_path / "out.jpg")

    assert os.path.getsize(tmp_path / "out.jpg") == 31367

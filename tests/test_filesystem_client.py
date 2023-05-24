import os.path
from pathlib import Path

import pytest
from pystac import Item
from stac_asset import FilesystemClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
def href() -> str:
    return str(Path(__file__).parent / "data" / "20201211_223832_CS2.jpg")


async def test_download(tmp_path: Path, href: str) -> None:
    client = FilesystemClient()
    await client.download_href(href, tmp_path / "out.jpg")
    assert os.path.getsize(tmp_path / "out.jpg") == 31367


async def test_item_download(tmp_path: Path, item: Item) -> None:
    client = FilesystemClient()
    await client.download_item(item, tmp_path)

    read_item = Item.from_file(str(tmp_path / "test-item.json"))
    asset = read_item.assets["data"]
    assert asset.href == "./20201211_223832_CS2.jpg"

    for link in read_item.links:
        if link.rel in ("child", "parent", "root", "collection"):
            assert os.path.exists(link.href)

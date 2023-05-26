import os.path
from pathlib import Path

import pytest
from pystac import Asset, Item
from stac_asset import (
    AssetDownloadWarning,
    AssetOverwriteException,
    FileNameStrategy,
    FilesystemClient,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def href() -> str:
    return str(Path(__file__).parent / "data" / "20201211_223832_CS2.jpg")


async def test_download(tmp_path: Path, href: str) -> None:
    async with FilesystemClient() as client:
        await client.download_href(href, tmp_path / "out.jpg")
        assert os.path.getsize(tmp_path / "out.jpg") == 31367


async def test_item_download(tmp_path: Path, item: Item) -> None:
    async with FilesystemClient() as client:
        item = await client.download_item(item, tmp_path)
        assert Path(tmp_path / f"{item.id}.json").exists()

        asset = item.assets["data"]
        assert asset.href == "./20201211_223832_CS2.jpg"


async def test_item_download_404(tmp_path: Path, item: Item) -> None:
    item.assets["missing-asset"] = Asset(href=str(Path(__file__).parent / "not-a-file"))
    async with FilesystemClient() as client:
        with pytest.warns(AssetDownloadWarning):
            await client.download_item(item, tmp_path)
    assert not (tmp_path / "not-a-file").exists()


async def test_item_download_no_directory(tmp_path: Path, item: Item) -> None:
    async with FilesystemClient() as client:
        with pytest.raises(FileNotFoundError):
            await client.download_item(
                item, tmp_path / "doesnt-exist", make_directory=False
            )


async def test_item_download_key(tmp_path: Path, item: Item) -> None:
    async with FilesystemClient() as client:
        await client.download_item(
            item, tmp_path, asset_file_name_strategy=FileNameStrategy.KEY
        )
        assert Path(tmp_path / "data.jpg").exists()


async def test_item_download_same_file_name(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    async with FilesystemClient() as client:
        with pytest.raises(AssetOverwriteException):
            await client.download_item(item, tmp_path)

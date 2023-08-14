import os.path
from asyncio import Queue
from pathlib import Path
from typing import Any

import pytest
import stac_asset
from pystac import Asset, Collection, Item, ItemCollection
from stac_asset import (
    AssetOverwriteError,
    CannotIncludeAndExclude,
    Config,
    DownloadError,
    DownloadStrategy,
    DownloadWarning,
    FileNameStrategy,
)

pytestmark = [
    pytest.mark.asyncio,
]


async def test_download_item(tmp_path: Path, item: Item) -> None:
    item = await stac_asset.download_item(item, tmp_path)
    assert os.path.exists(tmp_path / "20201211_223832_CS2.jpg")
    asset = item.assets["data"]
    assert asset.href == str(tmp_path / "20201211_223832_CS2.jpg")


async def test_download_item_with_file_name(tmp_path: Path, item: Item) -> None:
    await stac_asset.download_item(item, tmp_path, file_name="item.json")
    item = Item.from_file(str(tmp_path / "item.json"))
    assert item.assets["data"].href == "./20201211_223832_CS2.jpg"


async def test_download_missing_asset_error(tmp_path: Path, item: Item) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.raises(DownloadError):
        await stac_asset.download_item(
            item, tmp_path, config=Config(download_strategy=DownloadStrategy.ERROR)
        )


async def test_download_missing_asset_keep(
    tmp_path: Path, item: Item, data_path: Path
) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.warns(DownloadWarning):
        item = await stac_asset.download_item(
            item, tmp_path, config=Config(download_strategy=DownloadStrategy.KEEP)
        )
    assert item.assets["does-not-exist"].href == str(data_path / "not-a-file.md5")


async def test_download_missing_asset_delete(tmp_path: Path, item: Item) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.warns(DownloadWarning):
        item = await stac_asset.download_item(
            item, tmp_path, config=Config(download_strategy=DownloadStrategy.DELETE)
        )
    assert "does-not-exist" not in item.assets


async def test_download_item_collection(
    tmp_path: Path, item_collection: ItemCollection
) -> None:
    item_collection = await stac_asset.download_item_collection(
        item_collection, tmp_path
    )
    assert os.path.exists(tmp_path / "test-item" / "20201211_223832_CS2.jpg")
    asset = item_collection.items[0].assets["data"]
    assert asset.href == str(tmp_path / "test-item/20201211_223832_CS2.jpg")


async def test_download_item_collection_with_file_name(
    tmp_path: Path, item_collection: ItemCollection
) -> None:
    await stac_asset.download_item_collection(
        item_collection, tmp_path, file_name="item-collection.json"
    )
    item_collection = ItemCollection.from_file(str(tmp_path / "item-collection.json"))
    assert (
        item_collection.items[0].assets["data"].href
        == "./test-item/20201211_223832_CS2.jpg"
    )


async def test_download_collection(tmp_path: Path, collection: Collection) -> None:
    collection = await stac_asset.download_collection(
        collection, tmp_path, file_name="collection.json"
    )
    assert os.path.exists(tmp_path / "collection.json")
    assert os.path.exists(tmp_path / "20201211_223832_CS2.jpg")
    asset = collection.assets["data"]
    assert asset.href == "./20201211_223832_CS2.jpg"


async def test_item_download_no_directory(tmp_path: Path, item: Item) -> None:
    with pytest.raises(DownloadError):
        await stac_asset.download_item(
            item, tmp_path / "doesnt-exist", config=Config(make_directory=False)
        )


async def test_item_download_key(tmp_path: Path, item: Item) -> None:
    await stac_asset.download_item(
        item, tmp_path, config=Config(asset_file_name_strategy=FileNameStrategy.KEY)
    )
    assert Path(tmp_path / "data.jpg").exists()


async def test_item_download_same_file_name(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    with pytest.raises(AssetOverwriteError):
        await stac_asset.download_item(item, tmp_path)


async def test_include(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    await stac_asset.download_item(item, tmp_path, config=Config(include=["data"]))


async def test_exclude(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    await stac_asset.download_item(
        item, tmp_path, config=Config(exclude=["other-data"])
    )


async def test_cant_include_and_exclude(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    with pytest.raises(CannotIncludeAndExclude):
        await stac_asset.download_item(
            item, tmp_path, config=Config(include=["data"], exclude=["other-data"])
        )


@pytest.mark.network_access
async def test_multiple_clients(tmp_path: Path, item: Item) -> None:
    item.assets["remote"] = Asset(
        href="https://storage.googleapis.com/open-cogs/stac-examples/20201211_223832_CS2.jpg",
    )
    item = await stac_asset.download_item(
        item, tmp_path, config=Config(asset_file_name_strategy=FileNameStrategy.KEY)
    )


async def test_queue(tmp_path: Path, item: Item) -> None:
    queue: Queue[Any] = Queue()
    item = await stac_asset.download_item(item, tmp_path, queue=queue)
    assert not queue.empty()

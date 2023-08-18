import os.path
from asyncio import Queue
from pathlib import Path
from typing import Any

import pytest
import stac_asset
from pystac import Asset, Collection, Item, ItemCollection
from stac_asset import (
    AssetOverwriteError,
    Config,
    ConfigError,
    DownloadError,
    DownloadWarning,
    ErrorStrategy,
    FileNameStrategy,
    S3Client,
)

pytestmark = [
    pytest.mark.asyncio,
]


async def test_download_item(tmp_path: Path, item: Item) -> None:
    item = await stac_asset.download_item(item, tmp_path, infer_file_name=False)
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
        await stac_asset.download_item(item, tmp_path, config=Config(warn=False))


async def test_download_missing_asset_warn(tmp_path: Path, item: Item) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.warns(DownloadWarning):
        await stac_asset.download_item(item, tmp_path, config=Config(warn=True))


async def test_download_missing_asset_keep(
    tmp_path: Path, item: Item, data_path: Path
) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.warns(DownloadWarning):
        item = await stac_asset.download_item(
            item,
            tmp_path,
            config=Config(error_strategy=ErrorStrategy.KEEP, warn=True),
            infer_file_name=False,
        )
    assert item.assets["does-not-exist"].href == str(data_path / "not-a-file.md5")


async def test_download_missing_asset_delete(tmp_path: Path, item: Item) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.warns(DownloadWarning):
        item = await stac_asset.download_item(
            item,
            tmp_path,
            config=Config(error_strategy=ErrorStrategy.DELETE, warn=True),
        )
    assert "does-not-exist" not in item.assets


async def test_download_missing_asset_fail_fast(tmp_path: Path, item: Item) -> None:
    item.assets["does-not-exist"] = Asset("not-a-file.md5")
    with pytest.raises(FileNotFoundError):
        await stac_asset.download_item(
            item,
            tmp_path,
            config=Config(fail_fast=True),
        )


async def test_download_item_collection(
    tmp_path: Path, item_collection: ItemCollection
) -> None:
    item_collection = await stac_asset.download_item_collection(
        item_collection,
        tmp_path,
        file_name=None,
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
        item, tmp_path, config=Config(file_name_strategy=FileNameStrategy.KEY)
    )
    assert Path(tmp_path / "data.jpg").exists()


async def test_item_download_same_file_name(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    with pytest.raises(AssetOverwriteError):
        await stac_asset.download_item(item, tmp_path)


async def test_include(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    item = await stac_asset.download_item(
        item, tmp_path, config=Config(include=["data"])
    )
    assert len(item.assets) == 1


async def test_exclude(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    await stac_asset.download_item(
        item, tmp_path, config=Config(exclude=["other-data"])
    )


async def test_cant_include_and_exclude(tmp_path: Path, item: Item) -> None:
    item.assets["other-data"] = item.assets["data"].clone()
    with pytest.raises(ConfigError):
        await stac_asset.download_item(
            item, tmp_path, config=Config(include=["data"], exclude=["other-data"])
        )


@pytest.mark.network_access
async def test_multiple_clients(tmp_path: Path, item: Item) -> None:
    item.assets["remote"] = Asset(
        href="https://storage.googleapis.com/open-cogs/stac-examples/20201211_223832_CS2.jpg",
    )
    item = await stac_asset.download_item(
        item, tmp_path, config=Config(file_name_strategy=FileNameStrategy.KEY)
    )


@pytest.mark.network_access
async def test_preconfigured_clients(tmp_path: Path, item: Item) -> None:
    item.assets["remote"] = Asset(
        href="s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2023/092/068/LC09_L2SP_092068_20230522_20230524_02_T2/LC09_L2SP_092068_20230522_20230524_02_T2_thumb_small.jpeg",
    )
    s3_client = S3Client(requester_pays=True)
    item = await stac_asset.download_item(item, tmp_path, clients=[s3_client])


async def test_queue(tmp_path: Path, item: Item) -> None:
    queue: Queue[Any] = Queue()
    item = await stac_asset.download_item(item, tmp_path, queue=queue)
    assert not queue.empty()


async def test_asset_exists(item: Item) -> None:
    assert await stac_asset.asset_exists(item.assets["data"])
    assert not await stac_asset.asset_exists(Asset(href="not-a-file"))

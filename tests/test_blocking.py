from pathlib import Path

import stac_asset.blocking
from pystac import Collection, Item, ItemCollection
from stac_asset import Config


def test_download_item(tmp_path: Path, item: Item) -> None:
    item = stac_asset.blocking.download_item(item, tmp_path)
    item.validate()


def test_download_collection(tmp_path: Path, collection: Collection) -> None:
    collection = stac_asset.blocking.download_collection(collection, tmp_path)
    collection.validate()


def test_download_item_collection(
    tmp_path: Path, item_collection: ItemCollection
) -> None:
    item_collection = stac_asset.blocking.download_item_collection(
        item_collection, tmp_path
    )
    for item in item_collection:
        item.validate()


def test_download_asset(tmp_path: Path, item: Item) -> None:
    asset = stac_asset.blocking.download_asset(
        "data", item.assets["data"], tmp_path / "image.jpg", Config()
    )
    assert asset.href == str(tmp_path / "image.jpg")


def test_assert_asset_exists(tmp_path: Path, item: Item) -> None:
    stac_asset.blocking.assert_asset_exists(item.assets["data"])


def test_asset_exists(tmp_path: Path, item: Item) -> None:
    assert stac_asset.blocking.asset_exists(item.assets["data"])

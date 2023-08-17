from pathlib import Path
from typing import Any

import pytest
from pystac import Collection, Item, ItemCollection
from pytest import Config, Parser


@pytest.fixture
def asset_path() -> str:
    return str(Path(__file__).parent / "data" / "20201211_223832_CS2.jpg")


@pytest.fixture
def item_path() -> Path:
    return Path(__file__).parent / "data" / "item.json"


@pytest.fixture
def item_collection_path(tmp_path: Path, item: Item) -> Path:
    item.make_asset_hrefs_absolute()
    ItemCollection([item]).save_object(str(tmp_path / "item-collection.json"))
    return tmp_path / "item-collection.json"


@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture
def item(item_path: Path) -> Item:
    return Item.from_file(str(item_path))


@pytest.fixture
def collection() -> Collection:
    return Collection.from_file(str(Path(__file__).parent / "data" / "collection.json"))


@pytest.fixture
def item_collection(item: Item) -> ItemCollection:
    item.make_asset_hrefs_absolute()
    return ItemCollection([item])


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--network-access",
        action="store_true",
        default=False,
        help="run tests that access the network",
    )


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "network_access: marks tests as accessing the network, "
        "and disables them by default (enable with --network-access)",
    )


def pytest_collection_modifyitems(config: Config, items: Any) -> None:
    if config.getoption("--network-access"):
        return
    skip_network_access = pytest.mark.skip(reason="need --network-access option to run")
    for item in items:
        if "network_access" in item.keywords:
            item.add_marker(skip_network_access)

from typing import Any

import pytest
from pytest import Config, Parser


@pytest.fixture
def asset_href() -> str:
    return (
        "https://storage.googleapis.com/open-cogs/stac-examples/20201211_223832_CS2.jpg"
    )


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

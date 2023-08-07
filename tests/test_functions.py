from pathlib import Path

import pytest
import stac_asset
from pystac import Asset, Item
from stac_asset import Config, FileNameStrategy

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.network_access,
]


async def test_multiple_clients(tmp_path: Path, item: Item) -> None:
    item.assets["remote"] = Asset(
        href="https://storage.googleapis.com/open-cogs/stac-examples/20201211_223832_CS2.jpg",
    )
    item = await stac_asset.download_item(
        item, tmp_path, Config(asset_file_name_strategy=FileNameStrategy.KEY)
    )

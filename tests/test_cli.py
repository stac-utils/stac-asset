import json
import os
from pathlib import Path

import stac_asset._cli
from click.testing import CliRunner
from pystac import Item, ItemCollection


def test_download_item(tmp_path: Path, item_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        stac_asset._cli.cli,
        ["download", str(item_path), str(tmp_path)],
    )
    assert result.exit_code == 0


def test_download_item_stdin_stdout(tmp_path: Path, item: Item) -> None:
    previous_working_directory = os.getcwd()
    os.chdir(tmp_path)
    try:
        item_as_str = json.dumps(
            item.to_dict(include_self_link=True, transform_hrefs=False)
        )
        runner = CliRunner()
        result = runner.invoke(stac_asset._cli.cli, ["download"], input=item_as_str)
        assert result.exit_code == 0, result.stdout
        Item.from_dict(json.loads(result.stdout))
    finally:
        os.chdir(previous_working_directory)


def test_download_item_collection_stdin_stdout(
    tmp_path: Path, item_collection: ItemCollection
) -> None:
    previous_working_directory = os.getcwd()
    os.chdir(tmp_path)
    try:
        item_collection_as_str = json.dumps(
            item_collection.to_dict(transform_hrefs=False)
        )
        runner = CliRunner()
        result = runner.invoke(
            stac_asset._cli.cli, ["download"], input=item_collection_as_str
        )
        assert result.exit_code == 0, result.stdout
        ItemCollection.from_dict(json.loads(result.stdout))
    finally:
        os.chdir(previous_working_directory)

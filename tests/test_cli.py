import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner
from pystac import Item, ItemCollection

import stac_asset._cli


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
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(stac_asset._cli.cli, ["download"], input=item_as_str)
        assert result.exit_code == 0, result.stdout
        Item.from_dict(json.loads(result.stdout))
    finally:
        os.chdir(previous_working_directory)


def test_download_item_collection_stdin_stdout(
    tmp_path: Path, item_collection_path: Path
) -> None:
    runner = CliRunner()
    result = runner.invoke(
        stac_asset._cli.cli,
        [
            "download",
            str(item_collection_path),
            str(tmp_path),
            "--file-name",
            "item-collection.json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    ItemCollection.from_file(str(tmp_path / "item-collection.json"))


def test_download_item_collection_file_name(
    tmp_path: Path, item_collection: ItemCollection
) -> None:
    previous_working_directory = os.getcwd()
    os.chdir(tmp_path)
    try:
        item_collection_as_str = json.dumps(
            item_collection.to_dict(transform_hrefs=False)
        )
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            stac_asset._cli.cli, ["download"], input=item_collection_as_str
        )
        assert result.exit_code == 0, result.stdout
        ItemCollection.from_dict(json.loads(result.stdout))
    finally:
        os.chdir(previous_working_directory)


@pytest.mark.network_access
def test_download_item_s3_requester_pays(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        stac_asset._cli.cli,
        [
            "download",
            "https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-sr/items/LC09_L2SP_092068_20230607_20230609_02_T1_SR",
            str(tmp_path),
            "--s3-requester-pays",
            "-i",
            "thumbnail",
            "--alternate-assets",
            "s3",
            "--fail-fast",
        ],
    )
    assert result.exit_code == 0


def test_info(item_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        stac_asset._cli.cli,
        ["info", str(item_path)],
    )
    assert result.exit_code == 0, result.stdout

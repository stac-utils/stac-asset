from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from asyncio import Queue
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import click
import click_logging
import tabulate
import tqdm
from pystac import Asset, Item, ItemCollection

from . import Config, ErrorStrategy, _functions
from .client import Clients
from .config import (
    DEFAULT_HTTP_MAX_ATTEMPTS,
    DEFAULT_S3_MAX_ATTEMPTS,
    DEFAULT_S3_RETRY_MODE,
)
from .errors import DownloadError
from .messages import (
    ErrorAssetDownload,
    FinishAssetDownload,
    OpenUrl,
    SkipAssetDownload,
    StartAssetDownload,
    WriteChunk,
)
from .types import MessageQueue

logger = logging.getLogger(__name__)
click_logging.basic_config(logger)

# Needed until we drop Python 3.8
if TYPE_CHECKING:
    Tqdm = tqdm.tqdm[Any]
else:
    Tqdm = tqdm.tqdm


@click.group()
@click_logging.simple_verbosity_option(logger)  # type: ignore
def cli() -> None:
    """Work with STAC assets.

    See each subcommand's help text for more information:

        $ stac-asset download --help
        $ stac-asset info --help
    """


@cli.command()
@click.argument("href", required=False)
@click.argument("directory", required=False)
@click.option(
    "-p",
    "--path-template",
    help="String to be interpolated to specify where to store downloaded files",
)
@click.option(
    "-a",
    "--alternate-assets",
    help="Alternate asset hrefs to prefer, if available",
    multiple=True,
)
@click.option("-i", "--include", help="Asset keys to include", multiple=True)
@click.option(
    "-x",
    "--exclude",
    help="Asset keys to exclude (can't be used with include)",
    multiple=True,
)
@click.option("-f", "--file-name", help="The output file name")
@click.option(
    "-q",
    "--quiet",
    help="Do not print anything to standard output.",
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option(
    "--s3-requester-pays",
    help="If downloading via the s3 client, enable requester pays",
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option(
    "--s3-retry-mode",
    help="If downloading via the s3 client, the retry mode (standard, legacy, and "
    "adaptive)",
    default=DEFAULT_S3_RETRY_MODE,
)
@click.option(
    "--s3-max-attempts",
    help="If downloading via the s3 client, the max number of retries",
    default=DEFAULT_S3_MAX_ATTEMPTS,
)
@click.option(
    "--http-max-attempts",
    help="If downloading via the http client, the max number of retries",
    default=DEFAULT_HTTP_MAX_ATTEMPTS,
)
@click.option(
    "-k",
    "--keep",
    help=(
        "If warning on error, keep assets that couldn't be downloaded with their "
        "original hrefs. If false, delete those assets from the item."
    ),
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option(
    "--fail-fast",
    help="Fail immediately on download error, instead of waiting until all are "
    "complete.",
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option(
    "--overwrite",
    help="Overwrite existing files if they exist on the filesystem",
    default=False,
    is_flag=True,
    show_default=True,
)
# TODO add option to disable content type checking
def download(
    href: Optional[str],
    directory: Optional[str],
    path_template: Optional[str],
    alternate_assets: List[str],
    include: List[str],
    exclude: List[str],
    file_name: Optional[str],
    quiet: bool,
    s3_requester_pays: bool,
    s3_retry_mode: str,
    s3_max_attempts: int,
    http_max_attempts: int,
    keep: bool,
    fail_fast: bool,
    overwrite: bool,
) -> None:
    """Download STAC assets from an item or item collection.

    If href is not provided, or is ``-``, the item or item collection is parsed
    as JSON from standard input. If the directory is not provided, the current
    working directory is used.

    These three examples are equivalent, and download the assets to the current
    working directory:

        $ stac-asset download item.json

        $ stac-asset download item.json .

        $ cat item.json | stac-asset download

    To only include certain asset keys:

        $ stac-asset download -i asset-key-to-include item.json
    """
    asyncio.run(
        download_async(
            href,
            directory,
            path_template,
            alternate_assets,
            include,
            exclude,
            file_name,
            quiet,
            s3_requester_pays,
            s3_retry_mode,
            s3_max_attempts,
            http_max_attempts,
            keep=keep,
            fail_fast=fail_fast,
            overwrite=overwrite,
        )
    )


async def download_async(
    href: Optional[str],
    directory: Optional[str],
    path_template: Optional[str],
    alternate_assets: List[str],
    include: List[str],
    exclude: List[str],
    file_name: Optional[str],
    quiet: bool,
    s3_requester_pays: bool,
    s3_retry_mode: str,
    s3_max_attempts: int,
    http_max_attempts: int,
    keep: bool,
    fail_fast: bool,
    overwrite: bool,
) -> None:
    config = Config(
        alternate_assets=alternate_assets,
        include=include,
        exclude=exclude,
        s3_requester_pays=s3_requester_pays,
        s3_retry_mode=s3_retry_mode,
        s3_max_attempts=s3_max_attempts,
        http_max_attempts=http_max_attempts,
        error_strategy=ErrorStrategy.KEEP if keep else ErrorStrategy.DELETE,
        warn=not fail_fast,
        fail_fast=fail_fast,
        overwrite=overwrite,
    )

    input_dict = await read_as_dict(href, config)
    if directory is None:
        directory_str = os.getcwd()
    else:
        directory_str = str(directory)
    if quiet:
        messages = None
    else:
        messages = Queue()

    type_ = input_dict.get("type")
    if type_ is None:
        if not quiet:
            print("ERROR: missing 'type' field on input dictionary", file=sys.stderr)
        sys.exit(1)
    elif type_ == "Feature":
        item = Item.from_dict(input_dict)
        if href and href != "-":
            item.set_self_href(href)
            item.make_asset_hrefs_absolute()

        async def download() -> Union[Item, ItemCollection]:
            return await _functions.download_item(
                item,
                directory_str,
                file_name=file_name,
                infer_file_name=False,
                config=config,
                messages=messages,
            )

    elif type_ == "FeatureCollection":
        item_collection = ItemCollection.from_dict(input_dict)

        async def download() -> Union[Item, ItemCollection]:
            return await _functions.download_item_collection(
                item_collection,
                directory_str,
                path_template,
                file_name=file_name,
                config=config,
                messages=messages,
            )

    else:
        if not quiet:
            print(f"ERROR: unsupported 'type' field: {type_}", file=sys.stderr)
        sys.exit(2)

    task = asyncio.create_task(report_progress(messages))
    try:
        output = await download()
    except DownloadError:
        sys.exit(1)

    if messages:
        await messages.put(None)
    await task

    if not quiet:
        if file_name:
            print(f"Output STAC JSON written to {Path(directory_str) / file_name}")
        else:
            json.dump(output.to_dict(transform_hrefs=False), sys.stdout)


async def read_as_dict(href: Optional[str], config: Config) -> Dict[str, Any]:
    if href is None or href == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(await read(href, config))
    if not isinstance(data, dict):
        raise ValueError(f"input is not a dictionary: {data.__type__}")
    else:
        return data


async def read(href: str, config: Config) -> bytes:
    clients = Clients(config)
    async with await clients.get_client(href) as client:
        data = b""
        async for chunk in client.open_href(href):
            data += chunk
        return data


async def report_progress(messages: Optional[MessageQueue]) -> None:
    if messages is None:
        return
    progress_bar = tqdm.tqdm(
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    )
    sizes = dict()
    owners = dict()
    assets = 0
    done = 0
    errors = 0
    skips = 0
    total = 0
    n = 0
    progress_bar.set_postfix_str(f"{errors} errors")
    while True:
        message = await messages.get()
        if isinstance(message, StartAssetDownload):
            assets += 1
            if message.owner_id:
                owners[message.key] = message.owner_id
            progress_bar.set_description(f"{done}/{assets}")
        elif isinstance(message, OpenUrl):
            if message.size:
                total += message.size
                sizes[str(message.url)] = message.size
                progress_bar.reset(total=total)
                progress_bar.update(n)
        elif isinstance(message, SkipAssetDownload):
            skips += 1
            progress_bar.set_description_str(f"{done}/{assets}")
            progress_bar.set_postfix_str(f"{errors} errors, {skips} skips")
        elif isinstance(message, FinishAssetDownload):
            done += 1
            progress_bar.set_description_str(f"{done}/{assets}")
        elif isinstance(message, ErrorAssetDownload):
            done += 1
            errors += 1
            if message.href in sizes:
                total -= sizes[message.href]
                progress_bar.reset(total=total)
                progress_bar.update(n)
            progress_bar.set_postfix_str(f"{errors} errors, {skips} skips")
            progress_bar.set_description_str(f"{done}/{assets}")
            if message.key in owners:
                name = f"{owners[message.key]}[{message.key}]"
            else:
                name = f"[{message.key}]"
            progress_bar.write(f"ERROR: {name} - {message.error}", file=sys.stderr)
        elif isinstance(message, WriteChunk):
            n += message.size
            progress_bar.update(message.size)
        elif message is None:
            progress_bar.write("\n", file=sys.stderr)
            progress_bar.close()
            return


@dataclass
class Download:
    key: str
    item_id: Optional[str]
    href: str
    path: str
    progress_bar: Tqdm


@cli.command()
@click.argument("HREF", required=False)
@click.option(
    "-a",
    "--alternate-assets",
    help="Alternate asset hrefs to prefer, if available",
    multiple=True,
)
@click.option(
    "--s3-requester-pays",
    help="If checking via the s3 client, enable requester pays",
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option(
    "--s3-retry-mode",
    help="If checking via the s3 client, the retry mode (standard, legacy, and "
    "adaptive)",
    default=DEFAULT_S3_RETRY_MODE,
)
@click.option(
    "--s3-max-attempts",
    help="If checking via the s3 client, the max number of retries",
    default=DEFAULT_S3_MAX_ATTEMPTS,
)
@click.option(
    "--http-max-attempts",
    help="If checking via the http client, the max number of retries",
    default=DEFAULT_HTTP_MAX_ATTEMPTS,
)
def info(
    href: Optional[str],
    alternate_assets: List[str],
    s3_requester_pays: bool,
    s3_retry_mode: str,
    s3_max_attempts: int,
    http_max_attempts: int,
) -> None:
    asyncio.run(
        info_async(
            href=href,
            alternate_assets=alternate_assets,
            s3_requester_pays=s3_requester_pays,
            s3_max_attempts=s3_max_attempts,
            s3_retry_mode=s3_retry_mode,
            http_max_attempts=http_max_attempts,
        )
    )


async def info_async(
    href: Optional[str],
    alternate_assets: List[str],
    s3_requester_pays: bool,
    s3_retry_mode: str,
    s3_max_attempts: int,
    http_max_attempts: int,
) -> None:
    """Prints information about an item or item collection.

    $ stac-asset info item.json
    """
    config = Config(
        alternate_assets=alternate_assets,
        s3_requester_pays=s3_requester_pays,
        s3_retry_mode=s3_retry_mode,
        s3_max_attempts=s3_max_attempts,
        http_max_attempts=http_max_attempts,
    )
    input_dict = await read_as_dict(href, config)
    type_ = input_dict.get("type")
    tasks = set()
    clients = Clients(config)
    if type_ is None:
        print("ERROR: missing 'type' field on input dictionary", file=sys.stderr)
        sys.exit(1)
    elif type_ == "Feature":
        item = Item.from_dict(input_dict)
        if href and href != "-":
            item.set_self_href(href)
            item.make_asset_hrefs_absolute()
        for key, asset in item.assets.items():
            tasks.add(asyncio.create_task(get_asset_info(key, asset, config, clients)))
    elif type_ == "FeatureCollection":
        item_collection = ItemCollection.from_dict(input_dict)
        for item in item_collection.items:
            for key, asset in item.assets.items():
                tasks.add(
                    asyncio.create_task(get_asset_info(key, asset, config, clients))
                )
    else:
        print(f"ERROR: invalid 'type' field: {type_}", file=sys.stderr)
        sys.exit(1)

    asset_infos = await asyncio.gather(*tasks)
    await clients.close_all()

    table_dict = dict()
    for asset_info in asset_infos:
        assert isinstance(asset_info, AssetInfo)
        if asset_info.key not in table_dict:
            table_dict[asset_info.key] = {
                "Key": asset_info.key,
                "Client": asset_info.client,
                "Media type": asset_info.media_type,
                "Exists": asset_info.exists,
                "Note": asset_info.note,
            }
        else:
            if asset_info.exists != table_dict[asset_info.key]["Exists"]:
                table_dict[asset_info.key]["Exists"] = "Sometimes"
            if asset_info.client != table_dict[asset_info.key]["Client"]:
                table_dict[asset_info.key]["Client"] = "Various"
            if asset_info.media_type != table_dict[asset_info.key]["Media type"]:
                table_dict[asset_info.key]["Media type"] = "Various"
            if asset_info.note and table_dict[asset_info.key]["Note"]:
                table_dict[asset_info.key]["Note"] = (
                    str(table_dict[asset_info.key]["Note"]) + "\n" + asset_info.note
                )

    keys = sorted(table_dict.keys())
    headers = ["Asset", "Client", "Exists", "Media type", "Note"]
    table_data = list()
    for key in keys:
        value = table_dict[key]
        table_data.append(
            [
                value["Key"],
                value["Client"],
                value["Exists"],
                value["Media type"],
                value["Note"],
            ]
        )
    print(tabulate.tabulate(table_data, headers=headers))


async def get_asset_info(
    key: str, asset: Asset, config: Config, clients: Clients
) -> AssetInfo:
    # TODO refactor with asset_exists
    href = _functions.get_absolute_asset_href(asset, config.alternate_assets)
    if href:
        client = await clients.get_client(href)
        try:
            await client.assert_href_exists(href)
        except Exception as error:
            note = str(error)
            exists = False
        else:
            note = ""
            exists = True
        # TODO clients should probably specify this explicitly
        name = type(client).__name__.lower()
        # We can't use `removesuffix` because it was added in Python 3.9
        if name.endswith("client"):
            name = name[: -len("client")]
        return AssetInfo(
            key=key, client=name, media_type=asset.media_type, exists=exists, note=note
        )
    else:
        return AssetInfo(
            key=key,
            client="n/a",
            exists=False,
            note="Could not make absolute href",
        )


@dataclass
class AssetInfo:
    key: str
    client: str
    exists: bool
    media_type: Optional[str] = None
    note: str = ""


if __name__ == "__main__":
    cli()

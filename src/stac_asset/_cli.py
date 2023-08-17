import asyncio
import json
import logging
import os
import sys
from asyncio import Queue
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

import click
import click_logging
import tqdm
from pystac import Item, ItemCollection

from . import Config, ErrorStrategy, _functions
from .client import Clients
from .config import DEFAULT_S3_MAX_ATTEMPTS, DEFAULT_S3_RETRY_MODE
from .errors import DownloadError
from .messages import (
    ErrorAssetDownload,
    FinishAssetDownload,
    OpenUrl,
    SkipAssetDownload,
    StartAssetDownload,
    WriteChunk,
)

logger = logging.getLogger(__name__)
click_logging.basic_config(logger)

# Needed until we drop Python 3.8
if TYPE_CHECKING:
    AnyQueue = Queue[Any]
    Tqdm = tqdm.tqdm[Any]
else:
    AnyQueue = Queue
    Tqdm = tqdm.tqdm


@click.group()
def cli() -> None:
    """Work with STAC assets.

    See each subcommand's help text for more information:

        $ stac-asset download --help
    """


@cli.command()
@click_logging.simple_verbosity_option(logger)  # type: ignore
@click.argument("href", required=False)
@click.argument("directory", required=False)
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
    alternate_assets: List[str],
    include: List[str],
    exclude: List[str],
    file_name: Optional[str],
    quiet: bool,
    s3_requester_pays: bool,
    s3_retry_mode: str,
    s3_max_attempts: int,
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
            alternate_assets,
            include,
            exclude,
            file_name,
            quiet,
            s3_requester_pays,
            s3_retry_mode,
            s3_max_attempts,
            keep=keep,
            fail_fast=fail_fast,
            overwrite=overwrite,
        )
    )


async def download_async(
    href: Optional[str],
    directory: Optional[str],
    alternate_assets: List[str],
    include: List[str],
    exclude: List[str],
    file_name: Optional[str],
    quiet: bool,
    s3_requester_pays: bool,
    s3_retry_mode: str,
    s3_max_attempts: int,
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
        error_strategy=ErrorStrategy.KEEP if keep else ErrorStrategy.DELETE,
        warn=not fail_fast,
        fail_fast=fail_fast,
        overwrite=overwrite,
    )

    if href is None or href == "-":
        input_dict = json.load(sys.stdin)
    else:
        input_dict = json.loads(await read_file(href, config))
    if directory is None:
        directory_str = os.getcwd()
    else:
        directory_str = str(directory)

    if quiet:
        queue = None
    else:
        queue = Queue()

    type_ = input_dict.get("type")
    if type_ is None:
        if not quiet:
            print("ERROR: missing 'type' field on input dictionary", file=sys.stderr)
        sys.exit(1)
    elif type_ == "Feature":
        item = Item.from_dict(input_dict)
        if href:
            item.set_self_href(href)
            item.make_asset_hrefs_absolute()

        async def download() -> Union[Item, ItemCollection]:
            return await _functions.download_item(
                item,
                directory_str,
                file_name=file_name,
                infer_file_name=False,
                config=config,
                queue=queue,
            )

    elif type_ == "FeatureCollection":
        item_collection = ItemCollection.from_dict(input_dict)

        async def download() -> Union[Item, ItemCollection]:
            return await _functions.download_item_collection(
                item_collection,
                directory_str,
                file_name=file_name,
                config=config,
                queue=queue,
            )

    else:
        if not quiet:
            print(f"ERROR: unsupported 'type' field: {type_}", file=sys.stderr)
        sys.exit(2)

    task = asyncio.create_task(report_progress(queue))
    try:
        output = await download()
    except DownloadError:
        sys.exit(1)

    if queue:
        await queue.put(None)
    await task

    if not quiet:
        if file_name:
            print(f"Output STAC JSON written to {Path(directory_str) / file_name}")
        else:
            json.dump(output.to_dict(transform_hrefs=False), sys.stdout)


async def read_file(href: str, config: Config) -> bytes:
    clients = Clients(config)
    async with await clients.get_client(href) as client:
        data = b""
        async for chunk in client.open_href(href):
            data += chunk
        return data


async def report_progress(queue: Optional[AnyQueue]) -> None:
    if queue is None:
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
        message = await queue.get()
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


if __name__ == "__main__":
    cli()

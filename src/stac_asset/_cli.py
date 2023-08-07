import asyncio
import json
import logging
import os
import sys
from typing import List, Optional, Union

import click
import click_logging
from pystac import Item, ItemCollection

from . import Config, functions
from .config import DEFAULT_S3_MAX_ATTEMPTS, DEFAULT_S3_RETRY_MODE

logger = logging.getLogger(__name__)
click_logging.basic_config(logger)


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
    "-w",
    "--warn",
    help="Warn on download errors, instead of erroring",
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
    warn: bool,
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
    config = Config(
        alternate_assets=alternate_assets,
        include=include,
        exclude=exclude,
        file_name=file_name,
        s3_requester_pays=s3_requester_pays,
        s3_retry_mode=s3_retry_mode,
        s3_max_attempts=s3_max_attempts,
        warn=warn,
    )

    if href is None or href == "-":
        input_dict = json.load(sys.stdin)
    else:
        input_dict = json.loads(asyncio.run(read_file(href, config)))
    if directory is None:
        directory = os.getcwd()

    type_ = input_dict.get("type")
    if type_ is None:
        print("ERROR: missing 'type' field on input dictionary", file=sys.stderr)
        sys.exit(1)
    elif type_ == "Feature":
        item = Item.from_dict(input_dict)
        if href:
            item.set_self_href(href)
            item.make_asset_hrefs_absolute()
        output: Union[Item, ItemCollection] = asyncio.run(
            functions.download_item(
                item,
                directory,
                config=config,
            )
        )
    elif type_ == "FeatureCollection":
        item_collection = ItemCollection.from_dict(input_dict)
        output = asyncio.run(
            functions.download_item_collection(
                item_collection,
                directory,
                config=config,
            )
        )
    else:
        print(f"ERROR: unsupported 'type' field: {type_}", file=sys.stderr)
        sys.exit(2)

    if not quiet:
        json.dump(output.to_dict(transform_hrefs=False), sys.stdout)


async def read_file(href: str, config: Config) -> bytes:
    async with await functions.guess_client_class_from_href(href).from_config(
        config
    ) as client:
        data = b""
        async for chunk in client.open_href(href):
            data += chunk
        return data

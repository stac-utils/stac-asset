import asyncio
import json
import os
import sys
from typing import List, Optional, Union

import click
from pystac import Item, ItemCollection

from . import Config, functions


@click.group()
def cli() -> None:
    """Work with STAC assets.

    See each subcommand's help text for more information:

        $ stac-asset download --help
    """


@cli.command()
@click.argument("href", required=False)
@click.argument("directory", required=False)
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
    "-w",
    "--warn",
    help="Warn on download errors, instead of erroring",
    default=False,
    is_flag=True,
    show_default=True,
)
def download(
    href: Optional[str],
    directory: Optional[str],
    include: List[str],
    exclude: List[str],
    file_name: Optional[str],
    quiet: bool,
    s3_requester_pays: bool,
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
    if href is None or href == "-":
        input_dict = json.load(sys.stdin)
    else:
        input_dict = json.loads(asyncio.run(read_file(href)))
    if directory is None:
        directory = os.getcwd()

    config = Config(
        include=include,
        exclude=exclude,
        file_name=file_name,
        s3_requester_pays=s3_requester_pays,
        warn=warn,
    )

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


async def read_file(
    href: str,
) -> bytes:
    async with await functions.guess_client(href) as client:
        data = b""
        async for chunk in client.open_href(href):
            data += chunk
        return data

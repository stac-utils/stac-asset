import json
import os.path
from os import PathLike
from pathlib import Path
from typing import Any, AsyncIterator, Union

import aiofiles
from httpx import AsyncClient
from pystac import Asset

PathLikeObject = Union[PathLike[Any], str]
"""An object representing a file system path, except we exclude `bytes` because
`Path()` doesn't accept `bytes`.

A path-like object is either a str or bytes object representing a path, or an
object implementing the os.PathLike protocol. An object that supports the
os.PathLike protocol can be converted to a str or bytes file system path by
calling the os.fspath() function; os.fsdecode() and os.fsencode() can be used to
guarantee a str or bytes result instead, respectively. Introduced by PEP 519.

https://docs.python.org/3/glossary.html#term-path-like-object
"""

DEFAULT_ASSET_FILE_NAME = "asset.json"
"""When downloading an asset, the default file name for the asset itself."""


async def open_href(href: str) -> AsyncIterator[bytes]:
    """Open a file at the given href.

    Args:
        href: The href to open.

    Returns:
        AsyncIterator[bytes]: An iterator over the file's bytes.
    """
    client = AsyncClient()
    async with client.stream("GET", href) as response:
        async for chunk in response.aiter_bytes():
            yield chunk


async def open_asset(asset: Asset) -> AsyncIterator[bytes]:
    """Open a STAC Asset.

    Args:
        asset: The Asset to open.

    Returns:
        AsyncIterator[bytes]: An iterator over the Asset's bytes.
    """
    async for chunk in open_href(asset.href):
        yield chunk


async def download_href(href: str, path: PathLikeObject) -> None:
    """Download a file to the given path.

    The path's directory must exist.

    Args:
        href: The href to download.
        path: The location of the downloaded file.
    """
    async with aiofiles.open(path, mode="wb") as f:
        async for chunk in open_href(href):
            await f.write(chunk)


async def download_asset(
    asset: Asset,
    directory: PathLikeObject,
    make_directory: bool = False,
    asset_file_name: str = DEFAULT_ASSET_FILE_NAME,
) -> None:
    """Download a STAC Asset into the given directory.

    The file at the asset's href is downloaded into the directory. The asset is
    also downloaded into the directory, and its href is updated to point to the
    local file.

    Args:
        asset: The Asset to download.
        directory: The location of the downloaded file and Asset.
        make_directory: If true, create the directory (with exists_ok=True)
            before downloading.
    """
    directory_as_path = Path(directory)
    if make_directory:
        directory_as_path.mkdir(exist_ok=True)
    path = directory_as_path / os.path.basename(asset.href)
    await download_href(asset.href, path)
    asset.href = str(path)
    asset_as_str = json.dumps(asset.to_dict())
    async with aiofiles.open(directory_as_path / asset_file_name, "w") as f:
        await f.write(asset_as_str)

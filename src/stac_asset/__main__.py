import asyncio
import sys

from pystac import Item

import stac_asset

if len(sys.argv) != 3:
    print(f"Invalid number of arguments: expected=3, actual={len(sys.argv)}")
    print(
        "USAGE: python -m stac_asset http://stac-asset.test/path/to/the/item.json "
        "output/directory"
    )
    sys.exit(1)

item = Item.from_file(sys.argv[1])
asyncio.run(stac_asset.download_item(item, sys.argv[2], make_directory=True))

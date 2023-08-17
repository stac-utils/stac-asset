stac-asset
==========

**stac-asset** is a Python library for opening, downloading, and writing STAC assets across various network protocols, storage systems, and authentication regimes.

Motivation
----------

The `SpatioTemporal Asset Catalog (STAC) <https://stacspec.org>`_ is widely-used to index large holdings of geospatial assets and make them searchable.
STAC catalogs and APIs are encouraged to be fully open to the public, and they often are.
However, providing fully free and open access to the geospatial assets inside of a STAC catalog (e.g. the raster files themselves, not just their metadata) is much less common.
Whether its because of the cost of data egress, requirements around user access, or something else, many data providers put an authentication layer, or some other access restriction, in front of their data.

Over time, a set of access patterns have emerged around retrieving data from different cloud providers and from different systems.
This library aims to consolidate those patterns into a single repository and behind a single interface, so they can be used interchangeably and with the minimum amount of user configuration.

API
---

Let's say you have a :py:class:`pystac.Item` that you'd like to download, with its assets, to your local system.
You can use our top-level function, :py:func:`stac_asset.download_item` to do that.
This will download the item, with all of its assets, to the directory you specified, and update the asset hrefs to point to their new, downloaded locations.

.. code-block:: python

   import pystac
   import stac_asset

   href = "https://raw.githubusercontent.com/radiantearth/stac-spec/master/examples/simple-item.json"
   item = pystac.read_file(href)
   await stac_asset.download_item(item, ".")

If you have an :py:class:`pystac.ItemCollection`, you can download multiple items at once.
This can be particularly useful when you're querying a `STAC API <https://github.com/radiantearth/stac-api-spec>`_, e.g. with `pystac-client <https://github.com/stac-utils/pystac-client>`_.

.. code-block:: python

   import stac_asset
   from pystac_client import Client

   client = Client.open("https://earth-search.aws.element84.com/v1")
   item_search = client.search(
      collections=["sentinel-2-l2a"],
      query="grid:code=MGRS-13TDE",
      max_items=1
   )
   item_collection = item_search.item_collection()
   await stac_asset.download_item_collection(item_collection, ".")

If you run the above code, you'll probably see some errors.
That's because some assets in Earth Search's sentinel-2-l2a collections only have ``s3://`` hrefs that require `requester pays buckets <https://docs.aws.amazon.com/AmazonS3/latest/userguide/RequesterPaysBuckets.html>`_.
**stac-asset** uses the asset's href to guess the correct client to use for each download.
Each client can have its own configuration variables; see each client's documentation in :doc:`api` for more information.
To provide a configured client to the API, use ``clients``:

.. code-block:: python

   from stac_asset import S3Client

   s3_client = S3Client(requester_pays=True)
   await stac_asset.download_item_collection(item_collection, ".", clients=[s3_client])

See :doc:`api` for each available function and class.

CLI
---

Our :abbr:`Command-Line Interface (CLI)` provides pipe-enabled interface for downloading items and item collections.
We can use **pystac-client**'s CLI to search, and then pipe those results to our CLI.

.. code-block:: shell

   stac-client search https://earth-search.aws.element84.com/v1 \    
        -c sentinel-2-l2a \
        --query 'grid:code=MGRS-13TDE' \
        --max-items 1 | \
    stac-asset download

See :doc:`cli` for more information on the available subcommands and options.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   design-goals
   api
   cli

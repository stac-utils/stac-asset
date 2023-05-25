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

Usage
-----

Let's say you have a STAC Item that you'd like to download, with its assets, to your local system.
You can use our top-level function, :py:func:`stac_asset.download_item_from_href` to do that.
This will download the item, with all of its assets, to the directory you specified, and update the asset hrefs to point to the new item.

.. code-block:: python

   import stac_async

   href = "https://raw.githubusercontent.com/radiantearth/stac-spec/master/examples/simple-item.json"
   await stac_async.download_item_from_href(href, ".")

If you'd like to do multiple downloads, it's more efficient to re-use the same client.
Clients sometimes need to do cleanup after they're done, so they provide an asynchronous context manager interface to handle those cleanups:

.. code-block:: python

   from stac_async import HttpClient

   async with await HttpClient.default() as client:
      await client.download_item(item, ".")

We provide a suite of clients that are configured to access different data provides, using different communication protocols.
We have a :py:class:`~stac_asset.S3Client`:

.. code-block:: python

   from stac_asset import S3Client

   href = "s3://sentinel-cogs/sentinel-s2-l2a-cogs/42/L/TQ/2023/5/S2B_42LTQ_20230524_0_L2A/thumbnail.jpg"
   async with await S3Client.default() as client:
      await client.download_item(href, ".")

The :py:class:`~stac_asset.PlanetaryComputerClient` knows how to retrieve and store Shared Access Signatures (SASs) from the `Planetary Computer Authentication API <https://planetarycomputer.microsoft.com/docs/reference/sas/>`_ and use those SASes to access data from their Azure Blob Storage:

.. code-block:: python

   from stac_asset import PlanetaryComputerClient

   href = "https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/48/X/VR/2023/05/24/S2B_MSIL2A_20230524T084609_N0509_R107_T48XVR_20230524T120352.SAFE/GRANULE/L2A_T48XVR_A032451_20230524T084603/QI_DATA/T48XVR_20230524T084609_PVI.tif"
   async with await PlanetaryComputerClient.default() as client:
      await client.download_item(href, ".")

Other clients are provided for specific providers, such as :py:class:`~stac_asset.UsgsErosClient`.
See the :doc:`api` for information on all of the clients available.

Configuration
~~~~~~~~~~~~~

If there isn't a client that perfectly suits your needs, take one of the simpler clients and customize its public attributes.
For example, you could provide your own session to :py:meth:`~stac_asset.HttpClient()`:

.. code-block:: python

   from aiohttp import Session

   session = Session(headers={"foo": "bar")
   client = HttpClient(session)


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api
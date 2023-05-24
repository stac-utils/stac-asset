# stac-asset

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/gadomski/stac-asset/ci.yaml?style=for-the-badge)](https://github.com/gadomski/stac-asset/actions/workflows/ci.yaml)
[![Read the Docs](https://img.shields.io/readthedocs/stac-asset?style=for-the-badge)](https://stac-asset.readthedocs.io/en/stable/)
[![PyPI](https://img.shields.io/pypi/v/stac-asset?style=for-the-badge)](https://pypi.org/project/stac-asset)

Download STAC Assets using a variety of authentication schemes.

## Installation

```shell
pip install git+https://github.com/gadomski/stac-async
```

## Usage

Download a STAC [Item](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md) and all of its assets to a local directory.
Each Asset's href will be updated to point to the local file.

```python
from pystac import Item
href = "https://raw.githubusercontent.com/radiantearth/stac-spec/master/examples/simple-item.json"
item = Item.from_file(href)

from stac_async import HttpClient
client = await HttpClient.default()
await client.download_item(item, ".")
```

To download an item using the command line:

```python
python -m stac_asset https://raw.githubusercontent.com/radiantearth/stac-spec/master/examples/simple-item.json .
```

### Clients

This library comes with several clients, each tailored for a specific data provider model and authentication scheme.
Some clients require some setup before use; they are called out in this table, and the details are provided below.

| Name | Description | Notes |
| -- | -- | -- |
| `HttpClient` | Simple HTTP client without any authentication | |
| `S3Client` | Simple S3 client without any authentication | |
| `FilesystemClient` | Moves files from place to place on a local filesystem | Mostly used for testing |
| `PlanetaryComputerClient` | Signs urls with the [Planetary Computer Authentication API](https://planetarycomputer.microsoft.com/docs/reference/sas/) | No additional setup required, works out of the box |
| `UsgsErosClient` | Uses a token-based authentication workflow to download data, e.g. landsat, from USGS EROS | Requires creation of a personal access token, see section below |

#### USGS EROS

The USGS EROS system, which hosts landsat data, requires a personal access token to download assets.
Here's how to create and use your personal access token with **stac-asset**:

1. [Create a new personal access token](https://ers.cr.usgs.gov/password/appgenerate)
2. Set two environment variables:
    - `USGS_EROS_USERNAME` to your username (found in the top right of the web UI)
    - `USGS_EROS_PAT` to your personal access token
3. Use `UsgsErosClient.login()` to create a new client.

You can also provide your username and password to the `login` method.

## Design goals

As determined during a meeting at the Element 84 offices (formerly Azavea offices) on 2023-05-24.

- [x] `async`-first
- [ ] Allow range requests
- [x] Download functionality
- [x] Update STAC items to point to new hrefs on download
- [x] Allow byte-stream access
- [ ] Protocols:
  - [x] http
  - [x] s3
    - [ ] requestor pays
    - [ ] custom endpoint
  - [x] custom authentication
    - [x] Planetary Computer
    - [x] USGS EROS
    - [ ] NASA
- [ ] Copy directly from source to destination ("skip local")
- [ ] Add new assets to an item
- [ ] Update an existing asset
- [ ] Delete assets
- [ ] Templated paths on download
- [ ] (possible) Support the file extension's local path
- [ ] Checksum validation and creation
- [ ] CLI

## Contributing

Use Github [issues](https://github.com/gadomski/stac-asset/issues) to report bugs and request new features.
Use Github [pull requests](https://github.com/gadomski/stac-asset/pulls) to fix bugs and propose new features.

### Developing

Clone, install with the dev dependencies, and install **pre-commit**:

```shell
git clone git@github.com:gadomski/stac-asset.git
cd stac-asset
pip install '.[dev]'
pre-commit install
```

#### Testing

All network-touching tests are disabled by default, because we can't use [pytest-vcr](https://pytest-vcr.readthedocs.io/en/latest/) (<https://github.com/kevin1024/vcrpy/issues/597>), and repeatedly hitting the network during testing and CI is bad behavior.
To enable network-touching tests:

```shell
pytest --network-access
```

Some tests are client-specific and need your environment to be configured correctly.
See [each client's documentation](#clients) for instructions on setting up your environment for each client.
If your environment is not configured for a certain client, that client's tests are skipped.

#### Docs

Install the documentation dependencies:

```shell
pip install -e '.[docs]'
```

Then, build the docs:

```shell
make -C docs html && open docs/_build/html/index.html
```

It can be handy to use [sphinx-autobuild](https://pypi.org/project/sphinx-autobuild/) if you're doing a lot of doc work:

```shell
pip install sphinx-autobuild
sphinx-autobuild docs docs/_build/html
```

## License

[Apache-2.0](https://github.com/gadomski/stac-asset/blob/main/LICENSE)

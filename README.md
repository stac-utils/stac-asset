# stac-asset

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/stac-utils/stac-asset/ci.yaml?style=for-the-badge)](https://github.com/stac-utils/stac-asset/actions/workflows/ci.yaml)
[![Read the Docs](https://img.shields.io/readthedocs/stac-asset?style=for-the-badge)](https://stac-asset.readthedocs.io/en/stable/)
[![PyPI](https://img.shields.io/pypi/v/stac-asset?style=for-the-badge)](https://pypi.org/project/stac-asset)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg?style=for-the-badge)](./CODE_OF_CONDUCT)

Download STAC Assets using a variety of authentication schemes.

## Installation

```shell
pip install stac-asset
```

To use the command-line interface (CLI):

```shell
pip install 'stac-asset[cli]'
```

## Usage

### API

Here's how to download a STAC [Item](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md) and all of its assets to a local directory using the top-level function.
The correct [client](#clients) will be guessed from the assets' href.
Each asset's href will be updated to point to the local file.

```python
import stac_asset

href = "https://raw.githubusercontent.com/radiantearth/stac-spec/master/examples/simple-item.json"
await stac_asset.download_item_from_href(href, ".")
```

### CLI

To download an item using the command line:

```shell
stac-asset download https://raw.githubusercontent.com/radiantearth/stac-spec/master/examples/simple-item.json
```

To download all assets from the results of a [pystac-client](https://github.com/stac-utils/pystac-client) search, and save the item collection to a file named `item-collection.json`:

```shell
stac-client search https://planetarycomputer.microsoft.com/api/stac/v1 -c landsat-c2-l2 --max-items 1 | \
    stac-asset download > item-collection.json
```

If you'd like to only download certain assets, e.g. a preview image, you can use the include `-i` flag:

```shell
stac-client search https://planetarycomputer.microsoft.com/api/stac/v1 -c landsat-c2-l2 --max-items 1 | \
    stac-asset download -i rendered_preview -q
```

If you do a lot of downloads, you may want an alias:

```shell
alias stac-download="stac-asset download"
```

See [the documentation](https://stac-asset.readthedocs.io/en/stable/index.html) for more examples and complete API documentation.

### Clients

This library comes with several clients, each tailored for a specific data provider model and authentication scheme.
Some clients require some setup before use; they are called out in this table, and the details are provided below.

| Name | Description | Notes |
| -- | -- | -- |
| `HttpClient` | Simple HTTP client without any authentication | |
| `S3Client` | Simple S3 client | Use `requester_pays=True` in the client initializer to enable access to requester pays buckets, e.g. USGS landsat's public AWS archive |
| `FilesystemClient` | Moves files from place to place on a local filesystem | Mostly used for testing |
| `PlanetaryComputerClient` | Signs urls with the [Planetary Computer Authentication API](https://planetarycomputer.microsoft.com/docs/reference/sas/) | No additional setup required, works out of the box |
| `EarthdataClient` | Uses a token-based authentication to download data, from _some_ Earthdata providers, e.g. DAACs | Requires creation of a personal access token, see section below |

#### S3Client

To use the `requester_pays` option, you need to configure your AWS credentials.
See [the AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) for instructions.

#### Earthdata

You'll need a personal access token.

1. Create a new personal access token by going to <https://urs.earthdata.nasa.gov/profile> and then clicking "Generate Token" (you'll need to log in).
2. Set an enviornment variable named `EARTHDATA_PAT` to your token.
3. Use `EarthdataClient.default()` to create a new client.

You can also provide your token directly to `EarthdataClient.login()`.

#### USGS EROS

We used to have a USGS EROS client, but it turns out it was broken, and accessing landsat data via HTTP requires special authorization from USGS.
To access USGS landsat data, you can use `--s3-requester-pays`, e.g.:

```shell
stac-client search https://landsatlook.usgs.gov/stac-server \
        -c landsat-c2l2-sr \
        --intersects '{"type":"Point","coordinates":[-105.1019,40.1672]}' \
        --query "eo:cloud_cover<10" \
        --sortby='-properties.datetime' \
        --max-items 1 \
    | stac-asset download --s3-requester-pays -w -a s3 > landsat-c2l2-sr.json
```

You'll need to set up requester pays, as detailed [above](#s3client).

## Versioning

This project does its best to adhere to [semantic versioning](https://semver.org/).
Any module, class, constant, or function that does not begin with a `_` is considered part of our public API for versioning purposes.
Our command-line interface (CLI) is NOT considered part of our public API, and may change in breaking ways at any time.
If you need stability promises, use our API.

## Contributing

Use Github [issues](https://github.com/stac-utils/stac-asset/issues) to report bugs and request new features.
Use Github [pull requests](https://github.com/stac-utils/stac-asset/pulls) to fix bugs and propose new features.

## Developing

Clone, install with the dev dependencies, and install **pre-commit**:

```shell
git clone git@github.com:stac-utils/stac-asset.git
cd stac-asset
pip install '.[dev]'
pre-commit install
```

### Testing

All network-touching tests are disabled by default, because we can't use [pytest-vcr](https://pytest-vcr.readthedocs.io/en/latest/) (<https://github.com/kevin1024/vcrpy/issues/597>), and repeatedly hitting the network during testing and CI is bad behavior.
To enable network-touching tests:

```shell
pytest --network-access
```

Some tests are client-specific and need your environment to be configured correctly.
See [each client's documentation](#clients) for instructions on setting up your environment for each client.
If your environment is not configured for a certain client, that client's tests are skipped.

### Docs

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

[Apache-2.0](https://github.com/stac-utils/stac-asset/blob/main/LICENSE)

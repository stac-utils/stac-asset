# stac-asset

Read and write STAC Assets, using a variety of authentication schemes.

## Clients

Many clients require configuration before they can be used, e.g. for authentication.

### USGS EROS

The USGS EROS system, which hosts landsat data, requires a personal access token to download assets.
Here's use your personal access token with **stac-asset**:

1. [Create a new personal access token](https://ers.cr.usgs.gov/password/appgenerate)
2. Set two environment variables:
    - `USGS_EROS_USERNAME` to your username (found in the top right of the web UI)
    - `USGS_EROS_PAT` to your personal access token
3. Use `UsgsErosClient.login()` to create a new client.

You can also provide your username and password to the `login` function.

## Design goals

As determined during a meeting at the Element 84 offices (formerly Azavea offices) on 2023-05-24.

- `async`-first
- Allow range requests
- Download functionality
- Update STAC items to point to new hrefs on download
- Allow byte-stream access
- Protocols:
  - http
  - s3
    - requestor pays
    - custom endpoint
  - custom authentication
    - Planetary Computer
    - USGS
    - NASA
- Copy directly from source to destination ("skip local")
- Add new assets to an item
- Update an existing asset
- Delete assets
- Templated paths on download
- (possible) Support the file extension's local path
- Checksum validation and creation
- CLI

## Testing

All network-touching tests are disabled by default, because we can't use [pytest-vcr](https://pytest-vcr.readthedocs.io/en/latest/) (<https://github.com/kevin1024/vcrpy/issues/597>), and repeatedly hitting the network during testing and CI is bad behavior.
To enable network-touching tests:

```shell
pytest --network-access
```

Some tests are client-specific and need your environment to be configured correctly.
See [each client's documentation](#clients) for instructions on setting up your environment for each client.
If your environment is not configured, these tests are skipped.

# stac-asset

Read and write STAC Assets, using a variety of authentication schemes

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

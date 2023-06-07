# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Client.download_item_collection()` ([#20](https://github.com/gadomski/stac-asset/pull/20))
- Command-line interface ([#22](https://github.com/gadomski/stac-asset/pull/22))

### Changed

- Behavior of the item file name in `Client.download_item()` ([#20](https://github.com/gadomski/stac-asset/pull/20))

## [0.0.3] - 2023-05-31

### Added

- Warnings instead of errors if assets are missing
- Ability to save assets with their key as their file name
- Earthdata client

### Changed

- `download_item` returns the modified item

### Fixed

- All relative hrefs are made absolute on item download
- Clean up local files on download error

### Removed

- `open_asset` and `download_asset`

## [0.0.2] - 2023-05-25

### Added

- `stac_asset.download_item_from_href`
- Requester-pays support to the s3 client

### Fixed

- Cleaning up connections is easier thanks to `__aexit__` implementations

## [0.0.1] - 2023-05-24

Initial release.

[unreleased]: https://github.com/gadomski/stac-asset/compare/v0.0.3...HEAD
[0.0.3]: https://github.com/gadomski/stac-asset/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/gadomski/stac-asset/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/gadomski/stac-asset/releases/tag/v0.0.1

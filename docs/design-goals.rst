Design goals
============

As determined during a meeting at the Element 84 offices (formerly Azavea offices) on 2023-05-24.

* [x] `async`-first
* [ ] Allow range requests
* [x] Download functionality
* [x] Update STAC items to point to new hrefs on download
* [x] Allow byte-stream access
* [ ] Protocols:
    * [x] http
    * [x] s3
        * [x] requestor pays
        * [ ] custom endpoint
    * [x] custom authentication
        * [x] Planetary Computer
        * [x] USGS EROS
        * [x]  NASA
* [ ] Copy directly from source to destination ("skip local")
* [ ] Add new assets to an item
* [ ] Update an existing asset
* [ ] Delete assets
* [ ] Templated paths on download
* [ ] (possible) Support the file extension's local path
* [ ] Checksum validation and creation
* [x] CLI

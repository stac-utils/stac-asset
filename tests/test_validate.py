import pytest

from stac_asset import ContentTypeError, validate


def test_content_type() -> None:
    validate.content_type("foo", "foo")
    with pytest.raises(ContentTypeError):
        validate.content_type("foo", "bar")
    validate.content_type(
        "image/tiff", "image/tiff; application=geotiff; profile=cloud-optimized"
    )
    validate.content_type(
        "image/tiff; application=geotiff; profile=cloud-optimized", "image/tiff"
    )
    validate.content_type("text/xml", "application/xml")
    validate.content_type("application/xml", "text/xml")
    validate.content_type("binary/octet-stream", "doesn't matter")
    validate.content_type("application/octet-stream", "doesn't matter")

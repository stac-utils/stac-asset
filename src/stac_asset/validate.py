from .errors import ContentTypeError

ALLOWABLE_PAIRS = [
    ("image/tiff", "image/tiff; application=geotiff; profile=cloud-optimized")
]
IGNORED_CONTENT_TYPES = ["binary/octet-stream", "application/octet-stream"]


def content_type(actual: str, expected: str) -> None:
    """Validates that the actual content type matches the expected.

    This is more complicated than a simple string comparison, because we want to
    allow TIFF when COG is expected, etc.

    Args:
        actual: The actual content type
        expected: The expected content type

    Raises:
        ContentTypeError: Raised if the actual doesn't match the expected.
    """
    if (
        actual != expected
        and actual not in IGNORED_CONTENT_TYPES
        and (actual, expected) not in ALLOWABLE_PAIRS
        and (expected, actual) not in ALLOWABLE_PAIRS
    ):
        raise ContentTypeError(actual=actual, expected=expected)

from typing import Any, List


class AssetOverwriteException(Exception):
    """Raised when an asset would be overwritten during download."""

    def __init__(self, hrefs: List[str]) -> None:
        super().__init__(
            f"assets have the same file names and would overwrite each other: {hrefs}"
        )


class AssetDownloadException(Exception):
    """Raised when an asset was unable to be downloaded."""

    def __init__(self, key: str, href: str, err: Exception) -> None:
        self.key = key
        self.href = href
        self.err = err
        super().__init__(
            f"error when downloading asset '{key}' with href '{href}': {err}"
        )
        self.__cause__ = err


class AssetDownloadWarning(Warning):
    """A warning for when an asset couldn't be downloaded.

    Used when we don't want to cancel all downloads, but still inform the user
    about the problem.
    """


class CantIncludeAndExclude(Exception):
    """Raised if both include and exclude are passed to download."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            "can't use include and exclude in the same download call", *args, **kwargs
        )

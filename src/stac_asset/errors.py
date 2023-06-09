from typing import Any, List

from pystac import Asset


class AssetOverwriteError(Exception):
    """Raised when an asset would be overwritten during download."""

    def __init__(self, hrefs: List[str]) -> None:
        super().__init__(
            f"assets have the same file names and would overwrite each other: {hrefs}"
        )


class AssetDownloadError(Exception):
    """Raised when an asset was unable to be downloaded."""

    def __init__(self, key: str, asset: Asset, err: Exception) -> None:
        self.key = key
        self.asset = asset
        self.err = err
        super().__init__(
            f"error when downloading asset '{key}' with href '{asset.href}': {err}"
        )
        self.__cause__ = err


class DownloadWarning(Warning):
    """A warning for when something couldn't be downloaded.

    Used when we don't want to cancel all downloads, but still inform the user
    about the problem.
    """


class CantIncludeAndExclude(Exception):
    """Raised if both include and exclude are passed to download."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            "can't use include and exclude in the same download call", *args, **kwargs
        )


class SchemeError(Exception):
    """Raised if the scheme is inappropriate for the client."""


class DownloadError(Exception):
    """A collection of exceptions encountered while downloading."""

    def __init__(self, exceptions: List[Exception], *args: Any, **kwargs: Any) -> None:
        messages = list()
        for exception in exceptions:
            messages.append(str(exception))
        super().__init__("\n".join(messages), *args, **kwargs)

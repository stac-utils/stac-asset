from typing import Any, List


class AssetOverwriteError(Exception):
    """Raised when an asset would be overwritten during download."""

    def __init__(self, hrefs: List[str]) -> None:
        super().__init__(
            f"assets have the same file names and would overwrite each other: {hrefs}"
        )


class DownloadWarning(Warning):
    """A warning for when something couldn't be downloaded.

    Used when we don't want to cancel all downloads, but still inform the user
    about the problem.
    """


class ConfigError(Exception):
    """Raised if the configuration is not valid."""


class ContentTypeError(Exception):
    """The expected content type does not match the actual content type."""

    def __init__(self, actual: str, expected: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            f"the actual content type does not match the expected: actual={actual}, "
            f"expected={expected}",
            *args,
            **kwargs,
        )


class DownloadError(Exception):
    """A collection of exceptions encountered while downloading."""

    exceptions: List[Exception]

    def __init__(self, exceptions: List[Exception], *args: Any, **kwargs: Any) -> None:
        self.exceptions = exceptions
        messages = list()
        for exception in exceptions:
            messages.append(str(exception))
        super().__init__("\n".join(messages), *args, **kwargs)

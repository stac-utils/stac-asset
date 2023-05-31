from typing import List


class AssetOverwriteException(Exception):
    def __init__(self, hrefs: List[str]) -> None:
        super().__init__(
            f"assets have the same file names and would overwrite each other: {hrefs}"
        )


class AssetDownloadException(Exception):
    def __init__(self, key: str, href: str, err: Exception) -> None:
        self.key = key
        self.href = href
        self.err = err
        super().__init__(
            f"error when downloading asset '{key}' with href '{href}': {err}"
        )
        self.__cause__ = err


class AssetDownloadWarning(Warning):
    pass

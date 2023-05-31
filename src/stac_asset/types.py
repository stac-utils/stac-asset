from os import PathLike
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from typing import Any

    _PathLike = PathLike[Any]
else:
    _PathLike = PathLike

PathLikeObject = Union[_PathLike, str]
"""An object representing a file system path, except we exclude `bytes` because
`Path()` doesn't accept `bytes`.

A path-like object is either a str or bytes object representing a path, or an
object implementing the os.PathLike protocol. An object that supports the
os.PathLike protocol can be converted to a str or bytes file system path by
calling the os.fspath() function; os.fsdecode() and os.fsencode() can be used to
guarantee a str or bytes result instead, respectively. Introduced by PEP 519.

https://docs.python.org/3/glossary.html#term-path-like-object
"""

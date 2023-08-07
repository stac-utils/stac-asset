import pytest
from stac_asset import CannotIncludeAndExclude, Config


def test_validate_default() -> None:
    config = Config()
    config.validate()


def test_validate_include_and_exclude() -> None:
    config = Config(include=["foo"], exclude=["bar"])
    with pytest.raises(CannotIncludeAndExclude):
        config.validate()

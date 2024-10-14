import pytest

from stac_asset import Config, ConfigError


def test_validate_default() -> None:
    config = Config()
    config.validate()


def test_validate_include_and_exclude() -> None:
    config = Config(include=["foo"], exclude=["bar"])
    with pytest.raises(ConfigError):
        config.validate()


def test_warn_and_fail_fast() -> None:
    config = Config(warn=True, fail_fast=True)
    with pytest.raises(ConfigError):
        config.validate()

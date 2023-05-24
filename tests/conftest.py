import pytest


@pytest.fixture
def asset_href() -> str:
    return (
        "https://storage.googleapis.com/open-cogs/stac-examples/20201211_223832_CS2.jpg"
    )

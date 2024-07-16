import pytest
from aiohttp_oauth2_client.client import OAuth2Client
from aiohttp_oauth2_client.grant.authorization_code import AuthorizationCodeGrant
from aiohttp_oauth2_client.grant.client_credentials import ClientCredentialsGrant
from aiohttp_oauth2_client.grant.device_code import DeviceCodeGrant
from aiohttp_oauth2_client.grant.resource_owner_password_credentials import (
    ResourceOwnerPasswordCredentialsGrant,
)
from stac_asset import Config, HttpClient

pytestmark = [
    pytest.mark.asyncio,
]


@pytest.mark.vcr
async def test_href_exists() -> None:
    async with await HttpClient.from_config(Config()) as client:
        assert await client.href_exists("https://github.com/stac-utils/stac-asset")


async def test_default_http_timeout() -> None:
    async with await HttpClient.from_config(Config(http_client_timeout=42)) as client:
        assert client.session._client.timeout.total == 42


async def test_oauth2_device_code_config() -> None:
    config = Config(
        oauth2_grant="device_code",
        oauth2_token_url="https://example.com/token",
        oauth2_device_authorization_url="https://example.com/auth/device",
        oauth2_client_id="public",
    )
    async with await HttpClient.from_config(config) as client:
        assert isinstance(client.session, OAuth2Client)
        assert isinstance(client.session.grant, DeviceCodeGrant)


async def test_oauth2_authorization_code_config() -> None:
    config = Config(
        oauth2_grant="authorization_code",
        oauth2_token_url="https://example.com/token",
        oauth2_authorization_url="https://example.com/auth",
        oauth2_client_id="public",
        oauth2_pkce=False,
    )
    async with await HttpClient.from_config(config) as client:
        assert isinstance(client.session, OAuth2Client)
        assert isinstance(client.session.grant, AuthorizationCodeGrant)


async def test_oauth2_password_config() -> None:
    config = Config(
        oauth2_grant="password",
        oauth2_token_url="https://example.com/token",
        oauth2_client_id="public",
        oauth2_username="user",
        oauth2_password="secret",
    )
    async with await HttpClient.from_config(config) as client:
        assert isinstance(client.session, OAuth2Client)
        assert isinstance(client.session.grant, ResourceOwnerPasswordCredentialsGrant)


async def test_oauth2_client_credentials_config() -> None:
    config = Config(
        oauth2_grant="client_credentials",
        oauth2_token_url="https://example.com/token",
        oauth2_client_id="my-client",
        oauth2_client_secret="secret",
    )
    async with await HttpClient.from_config(config) as client:
        assert isinstance(client.session, OAuth2Client)
        assert isinstance(client.session.grant, ClientCredentialsGrant)

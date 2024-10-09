from __future__ import annotations

import warnings
from collections.abc import AsyncIterator
from types import TracebackType
from typing import TypeVar

from aiohttp import ClientError, ClientSession, ClientTimeout
from aiohttp_oauth2_client.client import OAuth2Client
from aiohttp_oauth2_client.models.grant import GrantType
from aiohttp_retry import JitterRetry, RetryClient
from aiohttp_retry.types import ClientType
from yarl import URL

from . import validate
from .client import Client
from .config import Config
from .errors import ContentTypeError
from .messages import OpenUrl
from .types import MessageQueue

T = TypeVar("T", bound="HttpClient")


class HttpClient(Client):
    """A simple client for making HTTP requests.

    By default, doesn't do any authentication.
    Configure the session to customize its behavior.
    """

    @classmethod
    async def from_config(cls: type[T], config: Config) -> T:
        """Creates an HTTP client with an aiohttp session object.

        To use OAuth2 access tokens, configure the
        :py:attr:`~stac_asset.Config.oauth2_grant` and the necessary parameters for the
        chosen grant type.

        OAuth2 device code grant (``urn:ietf:params:oauth:grant-type:device_code`` or ``device_code``):
          - :py:attr:`~stac_asset.Config.oauth2_token_url`
          - :py:attr:`~stac_asset.Config.oauth2_device_authorization_url`
          - :py:attr:`~stac_asset.Config.oauth2_client_id`
          - :py:attr:`~stac_asset.Config.oauth2_pkce`

        OAuth2 authorization code grant (``authorization_code``):
          - :py:attr:`~stac_asset.Config.oauth2_token_url`
          - :py:attr:`~stac_asset.Config.oauth2_authorization_url`
          - :py:attr:`~stac_asset.Config.oauth2_client_id`
          - :py:attr:`~stac_asset.Config.oauth2_pkce`

        OAuth2 resource owner password credentials grant (``password``):
          - :py:attr:`~stac_asset.Config.oauth2_token_url`
          - :py:attr:`~stac_asset.Config.oauth2_username`
          - :py:attr:`~stac_asset.Config.oauth2_password`
          - :py:attr:`~stac_asset.Config.oauth2_client_id`

        OAuth2 client credentials grant (``client_credentials``):
          - :py:attr:`~stac_asset.Config.oauth2_token_url`
          - :py:attr:`~stac_asset.Config.oauth2_client_id`
          - :py:attr:`~stac_asset.Config.oauth2_client_secret`
        """  # noqa: E501
        # TODO add basic auth
        timeout = ClientTimeout(total=config.http_client_timeout)
        if config.oauth2_grant is not None:
            if GrantType.DEVICE_CODE.endswith(config.oauth2_grant):
                from aiohttp_oauth2_client.grant.device_code import DeviceCodeGrant

                grant = DeviceCodeGrant(
                    token_url=config.oauth2_token_url,
                    device_authorization_url=config.oauth2_device_authorization_url,
                    client_id=config.oauth2_client_id,
                    pkce=config.oauth2_pkce,
                    **config.oauth2_extra,
                )
            elif config.oauth2_grant == GrantType.AUTHORIZATION_CODE:
                from aiohttp_oauth2_client.grant.authorization_code import (
                    AuthorizationCodeGrant,
                )

                grant = AuthorizationCodeGrant(
                    token_url=config.oauth2_token_url,
                    authorization_url=config.oauth2_authorization_url,
                    client_id=config.oauth2_client_id,
                    pkce=config.oauth2_pkce,
                    **config.oauth2_extra,
                )
            elif config.oauth2_grant == GrantType.RESOURCE_OWNER_PASSWORD_CREDENTIALS:
                from aiohttp_oauth2_client.grant.resource_owner_password_credentials import (  # noqa: E501
                    ResourceOwnerPasswordCredentialsGrant,
                )

                grant = ResourceOwnerPasswordCredentialsGrant(
                    token_url=config.oauth2_token_url,
                    username=config.oauth2_username,
                    password=config.oauth2_password,
                    client_id=config.oauth2_client_id,
                    **config.oauth2_extra,
                )
            elif config.oauth2_grant == GrantType.CLIENT_CREDENTIALS:
                from aiohttp_oauth2_client.grant.client_credentials import (
                    ClientCredentialsGrant,
                )

                grant = ClientCredentialsGrant(
                    token_url=config.oauth2_token_url,
                    client_id=config.oauth2_client_id,
                    client_secret=config.oauth2_client_secret,
                    **config.oauth2_extra,
                )
            else:
                raise ValueError("Unknown grant type")
            session = OAuth2Client(grant, timeout=timeout, headers=config.http_headers)
        else:
            session = ClientSession(timeout=timeout, headers=config.http_headers)
            session = RetryClient(
                client_session=session,
                retry_options=JitterRetry(
                    attempts=config.http_max_attempts, exceptions={ClientError}
                ),
            )
        return cls(session, config.http_assert_content_type)

    def __init__(
        self,
        session: ClientType,
        assert_content_type: bool,
    ) -> None:
        super().__init__()

        self.session: ClientSession = session
        """A aiohttp session that will be used for all requests."""

        self.assert_content_type: bool = assert_content_type
        """If true, check the asset's content type against the response from the server.

        See :py:func:`stac_asset.validate.content_type` for more information about
        the content type check.
        """

    async def open_url(
        self,
        url: URL,
        content_type: str | None = None,
        messages: MessageQueue | None = None,
        stream: bool | None = None,
    ) -> AsyncIterator[bytes]:
        """Opens a url with this client's session and iterates over its bytes.

        Args:
            url: The url to open
            content_type: The expected content type
            messages: An optional queue to use for progress reporting
            stream: If enabled, it uses the aiohttp streaming API

        Yields:
            AsyncIterator[bytes]: An iterator over the file's bytes

        Raises:
            :py:class:`aiohttp.ClientResponseError`: Raised if the response is not OK
        """
        if stream is None:
            stream = True
        async with self.session.get(url, allow_redirects=True) as response:
            response.raise_for_status()
            if content_type:
                try:
                    validate.content_type(
                        actual=response.content_type, expected=content_type
                    )
                except ContentTypeError as err:
                    if self.assert_content_type:
                        raise err
                    else:
                        warnings.warn(str(err))
            if messages:
                await messages.put(OpenUrl(url=url, size=response.content_length))
            if stream:
                async for chunk, _ in response.content.iter_chunks():
                    yield chunk
            else:
                content = await response.read()
                yield content

    async def assert_href_exists(self, href: str) -> None:
        """Asserts that the href exists.

        Uses a HEAD request.
        """
        async with self.session.head(href) as response:
            response.raise_for_status()

    async def close(self) -> None:
        """Close this http client.

        Closes the underlying session.
        """
        await self.session.close()

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self.close()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field

from .errors import ConfigError
from .strategy import ErrorStrategy, FileNameStrategy

DEFAULT_S3_REGION_NAME = "us-west-2"
DEFAULT_S3_RETRY_MODE = "adaptive"
DEFAULT_S3_MAX_ATTEMPTS = 10
DEFAULT_HTTP_CLIENT_TIMEOUT = 300
DEFAULT_HTTP_MAX_ATTEMPTS = 10


@dataclass
class Config:
    """Configuration for downloading items and their assets."""

    alternate_assets: list[str] = field(default_factory=list)
    """Alternate asset keys to prefer, if available."""

    file_name_strategy: FileNameStrategy = FileNameStrategy.FILE_NAME
    """The file name strategy to use when downloading assets."""

    warn: bool = False
    """If an error occurs during download, warn instead of raising the error."""

    fail_fast: bool = False
    """If an error occurs during download, fail immediately.

    By default, all downloads are completed before raising/warning any errors.
    Mutually exclusive with ``warn``.
    """

    error_strategy: ErrorStrategy = ErrorStrategy.DELETE
    """The strategy to use when errors occur during download."""

    exclude: list[str] = field(default_factory=list)
    """Assets to exclude from the download.

    Mutually exclusive with ``include``.
    """

    include: list[str] = field(default_factory=list)
    """Assets to include in the download.

    Mutually exclusive with ``exclude``.
    """

    make_directory: bool = True
    """Whether to create the output directory.

    If False, and the output directory does not exist, an error will be raised.
    """

    clean: bool = True
    """If true, clean up the downloaded file if it errors."""

    overwrite: bool = False
    """Download files even if they already exist locally."""

    client_override: str | None = None
    """Use the same client for all asset requests.

    If not set, each asset's client will be guessed from its href.
    """

    http_client_timeout: float | None = DEFAULT_HTTP_CLIENT_TIMEOUT
    """Total number of seconds for the whole request."""

    http_max_attempts: int = DEFAULT_HTTP_MAX_ATTEMPTS
    """The maximum number of attempts when downloading assets via http."""

    http_assert_content_type: bool = False
    """If true, check the asset's content type against the response from the server."""

    http_headers: dict[str, str] = field(default_factory=dict)
    """Extra headers to include in every http request."""

    earthdata_token: str | None = None
    """A token for logging in to Earthdata."""

    s3_region_name: str = DEFAULT_S3_REGION_NAME
    """Default s3 region."""

    s3_requester_pays: bool = False
    """If using the s3 client, enable requester pays."""

    s3_retry_mode: str = DEFAULT_S3_RETRY_MODE
    """The retry mode to use for s3 requests."""

    s3_max_attempts: int = DEFAULT_S3_MAX_ATTEMPTS
    """The maximum number of attempts when downloading assets from s3."""

    s3_endpoint_url: str | None = None
    """Set an optional custom endpoint url for s3."""

    oauth2_grant: str | None = field(default=os.getenv("OAUTH2_GRANT"))
    """OAuth2 grant type.

    If a value is provided for this field,
    the :py:class:`~stac_asset.http_client.HttpClient` will be configured with
    support for OAuth2 access tokens.
    Can be configured with the ``OAUTH2_GRANT`` environment variable.
    """

    oauth2_token_url: str | None = field(default=os.getenv("OAUTH2_TOKEN_URL"))
    """OAuth2 token URL.

    Can be configured with the ``OAUTH2_TOKEN_URL`` environment variable.
    """

    oauth2_authorization_url: str | None = field(
        default=os.getenv("OAUTH2_AUTHORIZATION_URL")
    )
    """OAuth2 authorization URL.

    Can be configured with the ``OAUTH2_AUTHORIZATION_URL`` environment variable.
    """

    oauth2_device_authorization_url: str | None = field(
        default=os.getenv("OAUTH2_DEVICE_AUTHORIZATION_URL")
    )
    """OAuth2 device authorization URL.

    Can be configured with the ``OAUTH2_DEVICE_AUTHORIZATION_URL`` environment variable.
    """

    oauth2_client_id: str | None = field(default=os.getenv("OAUTH2_CLIENT_ID"))
    """OAuth2 client identifier.

    Can be configured with the ``OAUTH2_CLIENT_ID`` environment variable.
    """

    oauth2_client_secret: str | None = field(default=os.getenv("OAUTH2_CLIENT_SECRET"))
    """OAuth2 client secret.

    Can be configured with the ``OAUTH2_CLIENT_SECRET`` environment variable.
    """

    oauth2_pkce: bool = field(
        default=os.getenv("OAUTH2_PKCE", "true").lower() not in ("false", "0")
    )
    """OAuth2 Proof Key for Code Exchange.

    Can be configured with the ``OAUTH2_PKCE`` environment variable.
    By default, PKCE is enabled.
    """

    oauth2_username: str | None = field(default=os.getenv("OAUTH2_USERNAME"))
    """OAuth2 username for resource owner password credentials grant.

    Can be configured with the ``OAUTH2_USERNAME`` environment variable.
    """

    oauth2_password: str | None = field(default=os.getenv("OAUTH2_PASSWORD"))
    """OAuth2 password for resource owner password credentials grant.

    Can be configured with the ``OAUTH2_PASSWORD`` environment variable.
    """

    oauth2_extra: dict[str, str] = field(default_factory=dict)
    """Extra configuration options for the OAuth2 grant.
    """

    def validate(self) -> None:
        """Validates this configuration.

        Raises:
            CannotIncludeAndExclude: ``include`` and ``exclude`` are mutually exclusive
        """
        if self.include and self.exclude:
            raise ConfigError(
                f"cannot provide both include and exclude: include={self.include}, "
                "exclude={self.exclude}"
            )
        if self.warn and self.fail_fast:
            raise ConfigError("cannot warn and fail fast as the same time")

    def copy(self) -> Config:
        """Returns a deep copy of this config.

        Returns:
            Config: A deep copy of this config.
        """
        return copy.deepcopy(self)

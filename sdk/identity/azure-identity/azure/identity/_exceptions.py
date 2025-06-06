# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
from typing import Any, Iterable, Optional

from azure.core.exceptions import ClientAuthenticationError


class CredentialUnavailableError(ClientAuthenticationError):
    """The credential did not attempt to authenticate because required data or state is unavailable."""


class AuthenticationRequiredError(CredentialUnavailableError):
    """Interactive authentication is required to acquire a token.

    This error is raised only by interactive user credentials configured not to automatically prompt for user
    interaction as needed. Its properties provide additional information that may be required to authenticate. The
    control_interactive_prompts sample demonstrates handling this error by calling a credential's "authenticate"
    method.

    :param str scopes: Scopes requested during the failed authentication
    :param str message: An error message explaining the reason for the exception.
    :param str claims: Additional claims required in the next authentication.
    """

    def __init__(
        self, scopes: Iterable[str], message: Optional[str] = None, claims: Optional[str] = None, **kwargs: Any
    ) -> None:
        self._claims = claims
        self._scopes = scopes
        if not message:
            message = "Interactive authentication is required to get a token. Call 'authenticate' to begin."
        super(AuthenticationRequiredError, self).__init__(message=message, **kwargs)

    @property
    def scopes(self) -> Iterable[str]:
        """Scopes requested during the failed authentication.

        :return: Scopes requested during the failed authentication.
        :rtype: ~typing.Iterable[str]
        """
        return self._scopes

    @property
    def claims(self) -> Optional[str]:
        """Additional claims required in the next authentication.

        :return: Additional claims required in the next authentication, or None if no additional claims are required.
        :rtype: str or None
        """
        return self._claims

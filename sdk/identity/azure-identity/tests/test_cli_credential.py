# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
from datetime import datetime
from itertools import product
import json
import re

from azure.identity import AzureCliCredential, CredentialUnavailableError
from azure.identity._constants import EnvironmentVariables
from azure.identity._credentials.azure_cli import CLI_NOT_FOUND, NOT_LOGGED_IN
from azure.core.exceptions import ClientAuthenticationError

import subprocess
import pytest

from helpers import mock, INVALID_CHARACTERS, INVALID_SUBSCRIPTION_CHARACTERS, GET_TOKEN_METHODS

CHECK_OUTPUT = AzureCliCredential.__module__ + ".subprocess.check_output"

TEST_ERROR_OUTPUTS = (
    '{"accessToken": "secret value',
    '{"accessToken": "secret value"',
    '{"accessToken": "secret value and some other nonsense"',
    '{"accessToken": "secret value", some invalid json, "accessToken": "secret value"}',
    '{"accessToken": "secret value"}',
    '{"accessToken": "secret value", "subscription": "some-guid", "tenant": "some-guid", "tokenType": "Bearer"}',
    "no secrets or json here",
    "{}",
)


def raise_called_process_error(return_code, output="", cmd="...", stderr=""):
    error = subprocess.CalledProcessError(return_code, cmd=cmd, output=output, stderr=stderr)
    return mock.Mock(side_effect=error)


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_no_scopes(get_token_method):
    """The credential should raise ValueError when get_token is called with no scopes"""

    with pytest.raises(ValueError):
        getattr(AzureCliCredential(), get_token_method)()


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_multiple_scopes(get_token_method):
    """The credential should raise ValueError when get_token is called with more than one scope"""

    with pytest.raises(ValueError):
        getattr(AzureCliCredential(), get_token_method)("one scope", "and another")


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_invalid_tenant_id(get_token_method):
    """Invalid tenant IDs should raise ValueErrors."""

    for c in INVALID_CHARACTERS:
        with pytest.raises(ValueError):
            AzureCliCredential(tenant_id="tenant" + c)

        with pytest.raises(ValueError):
            kwargs = {"tenant_id": "tenant" + c}
            if get_token_method == "get_token_info":
                kwargs = {"options": kwargs}
            getattr(AzureCliCredential(), get_token_method)("scope", **kwargs)


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_invalid_scopes(get_token_method):
    """Scopes with invalid characters should raise ValueErrors."""

    for c in INVALID_CHARACTERS:
        with pytest.raises(ValueError):
            getattr(AzureCliCredential(), get_token_method)("scope" + c)


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_subscription(get_token_method):
    """The credential should accept a subscription ID"""

    subscription = "foo subscription"
    credential = AzureCliCredential(subscription=subscription)
    assert credential.subscription == subscription

    def fake_check_output(command_line, **_):
        assert "--subscription" in command_line
        subscription_id_index = command_line.index("--subscription")
        assert command_line[subscription_id_index + 1]
        return json.dumps(
            {
                "expiresOn": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "accessToken": "access-token",
                "subscription": subscription,
                "tenant": "tenant",
                "tokenType": "Bearer",
            }
        )

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, fake_check_output):
            token = getattr(credential, get_token_method)("scope")
            assert token.token == "access-token"


def test_invalid_subscriptons():
    """Subscriptions with invalid characters should raise ValueErrors."""

    for c in INVALID_SUBSCRIPTION_CHARACTERS:
        with pytest.raises(ValueError):
            AzureCliCredential(subscription="subscription" + c)


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_get_token(get_token_method):
    """The credential should parse the CLI's output to an AccessToken"""

    access_token = "access token"
    expected_expires_on = 1602015811
    successful_output = json.dumps(
        {
            "expiresOn": datetime.fromtimestamp(expected_expires_on).strftime("%Y-%m-%d %H:%M:%S.%f"),
            "accessToken": access_token,
            "subscription": "some-guid",
            "tenant": "some-guid",
            "tokenType": "Bearer",
        }
    )

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, mock.Mock(return_value=successful_output)):
            token = getattr(AzureCliCredential(), get_token_method)("scope")

    assert token.token == access_token
    assert type(token.expires_on) == int
    assert token.expires_on == expected_expires_on


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_expires_on_used(get_token_method):
    """Test that 'expires_on' is preferred over 'expiresOn'."""
    expires_on = 1602015811
    successful_output = json.dumps(
        {
            "expiresOn": datetime.fromtimestamp(1555555555).strftime("%Y-%m-%d %H:%M:%S.%f"),
            "expires_on": expires_on,
            "accessToken": "access token",
            "subscription": "some-guid",
            "tenant": "some-guid",
            "tokenType": "Bearer",
        }
    )

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, mock.Mock(return_value=successful_output)):
            token = getattr(AzureCliCredential(), get_token_method)("scope")

    assert token.expires_on == expires_on


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_expires_on_string(get_token_method):
    """Test that 'expires_on' still works if it's a string."""
    expires_on = 1602015811
    successful_output = json.dumps(
        {
            "expires_on": f"{expires_on}",
            "accessToken": "access token",
            "subscription": "some-guid",
            "tenant": "some-guid",
            "tokenType": "Bearer",
        }
    )

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, mock.Mock(return_value=successful_output)):
            token = getattr(AzureCliCredential(), get_token_method)("scope")

    assert type(token.expires_on) == int
    assert token.expires_on == expires_on


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_cli_not_installed(get_token_method):
    """The credential should raise CredentialUnavailableError when the CLI isn't installed"""
    with mock.patch("shutil.which", return_value=None):
        with pytest.raises(CredentialUnavailableError, match=CLI_NOT_FOUND):
            getattr(AzureCliCredential(), get_token_method)("scope")


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_cannot_execute_shell(get_token_method):
    """The credential should raise CredentialUnavailableError when the subprocess doesn't start"""

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, mock.Mock(side_effect=OSError())):
            with pytest.raises(CredentialUnavailableError):
                getattr(AzureCliCredential(), get_token_method)("scope")


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_not_logged_in(get_token_method):
    """When the CLI isn't logged in, the credential should raise CredentialUnavailableError"""

    stderr = "ERROR: Please run 'az login' to setup account."
    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, raise_called_process_error(1, stderr=stderr)):
            with pytest.raises(CredentialUnavailableError, match=NOT_LOGGED_IN):
                getattr(AzureCliCredential(), get_token_method)("scope")


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_aadsts_error(get_token_method):
    """When the CLI isn't logged in, the credential should raise CredentialUnavailableError"""

    stderr = "ERROR: AADSTS70043: The refresh token has expired, Please run 'az login' to setup account."
    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, raise_called_process_error(1, stderr=stderr)):
            with pytest.raises(ClientAuthenticationError, match=stderr):
                getattr(AzureCliCredential(), get_token_method)("scope")


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_unexpected_error(get_token_method):
    """When the CLI returns an unexpected error, the credential should raise an error containing the CLI's output"""

    stderr = "something went wrong"
    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, raise_called_process_error(42, stderr=stderr)):
            with pytest.raises(ClientAuthenticationError, match=stderr):
                getattr(AzureCliCredential(), get_token_method)("scope")


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_unexpected_error_no_stderr(get_token_method):
    """When the CLI returns an unexpected error with no stderr captured, the credential should raise an error with a str output"""

    stderr = None
    default_message = "Failed to invoke Azure CLI"
    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, raise_called_process_error(42, stderr=stderr)):
            with pytest.raises(ClientAuthenticationError, match=stderr):
                getattr(AzureCliCredential(), get_token_method)("scope")


@pytest.mark.parametrize("output,get_token_method", product(TEST_ERROR_OUTPUTS, GET_TOKEN_METHODS))
def test_parsing_error_does_not_expose_token(output, get_token_method):
    """Errors during CLI output parsing shouldn't expose access tokens in that output"""

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, mock.Mock(return_value=output)):
            with pytest.raises(ClientAuthenticationError) as ex:
                getattr(AzureCliCredential(), get_token_method)("scope")

    assert "secret value" not in str(ex.value)
    assert "secret value" not in repr(ex.value)


@pytest.mark.parametrize("output,get_token_method", product(TEST_ERROR_OUTPUTS, GET_TOKEN_METHODS))
def test_subprocess_error_does_not_expose_token(output, get_token_method):
    """Errors from the subprocess shouldn't expose access tokens in CLI output"""

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, raise_called_process_error(1, output=output)):
            with pytest.raises(ClientAuthenticationError) as ex:
                getattr(AzureCliCredential(), get_token_method)("scope")

    assert "secret value" not in str(ex.value)
    assert "secret value" not in repr(ex.value)


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_timeout(get_token_method):
    """The credential should raise CredentialUnavailableError when the subprocess times out"""

    from subprocess import TimeoutExpired

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, mock.Mock(side_effect=TimeoutExpired("", 42))) as check_output_mock:
            with pytest.raises(CredentialUnavailableError):
                getattr(AzureCliCredential(process_timeout=42), get_token_method)("scope")

    # Ensure custom timeout is passed to subprocess
    _, kwargs = check_output_mock.call_args
    assert "timeout" in kwargs
    assert kwargs["timeout"] == 42


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_multitenant_authentication_class(get_token_method):
    default_tenant = "first-tenant"
    first_token = "***"
    second_tenant = "second-tenant"
    second_token = first_token * 2

    def fake_check_output(command_line, **_):
        tenant_index = command_line.index("--tenant") if "--tenant" in command_line else None
        tenant = command_line[tenant_index + 1] if tenant_index is not None else default_tenant
        assert tenant in (default_tenant, second_tenant), 'unexpected tenant "{}"'.format(tenant)
        return json.dumps(
            {
                "expiresOn": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "accessToken": first_token if tenant == default_tenant else second_token,
                "subscription": "some-guid",
                "tenant": tenant,
                "tokenType": "Bearer",
            }
        )

    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, fake_check_output):
            token = getattr(AzureCliCredential(), get_token_method)("scope")
            assert token.token == first_token

            token = getattr(AzureCliCredential(tenant_id=default_tenant), get_token_method)("scope")
            assert token.token == first_token

            token = getattr(AzureCliCredential(tenant_id=second_tenant), get_token_method)("scope")
            assert token.token == second_token


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_multitenant_authentication(get_token_method):
    default_tenant = "first-tenant"
    first_token = "***"
    second_tenant = "second-tenant"
    second_token = first_token * 2

    def fake_check_output(command_line, **_):
        tenant_index = command_line.index("--tenant") if "--tenant" in command_line else None
        tenant = command_line[tenant_index + 1] if tenant_index is not None else default_tenant
        assert tenant in (default_tenant, second_tenant), 'unexpected tenant "{}"'.format(tenant)
        return json.dumps(
            {
                "expiresOn": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "accessToken": first_token if tenant == default_tenant else second_token,
                "subscription": "some-guid",
                "tenant": tenant,
                "tokenType": "Bearer",
            }
        )

    credential = AzureCliCredential()
    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, fake_check_output):
            token = getattr(credential, get_token_method)("scope")
            assert token.token == first_token

            kwargs = {"tenant_id": default_tenant}
            if get_token_method == "get_token_info":
                kwargs = {"options": kwargs}
            token = getattr(credential, get_token_method)("scope", **kwargs)
            assert token.token == first_token

            kwargs = {"tenant_id": second_tenant}
            if get_token_method == "get_token_info":
                kwargs = {"options": kwargs}
            token = getattr(credential, get_token_method)("scope", **kwargs)
            assert token.token == second_token

            # should still default to the first tenant
            token = getattr(credential, get_token_method)("scope")
            assert token.token == first_token


@pytest.mark.parametrize("get_token_method", GET_TOKEN_METHODS)
def test_multitenant_authentication_not_allowed(get_token_method):
    expected_tenant = "expected-tenant"
    expected_token = "***"

    def fake_check_output(command_line, **_):
        tenant_index = command_line.index("--tenant") if "--tenant" in command_line else None
        tenant = command_line[tenant_index + 1] if tenant_index is not None else None
        assert tenant is None or tenant == expected_tenant
        return json.dumps(
            {
                "expiresOn": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "accessToken": expected_token,
                "subscription": "some-guid",
                "tenant": expected_token,
                "tokenType": "Bearer",
            }
        )

    credential = AzureCliCredential()
    with mock.patch("shutil.which", return_value="az"):
        with mock.patch(CHECK_OUTPUT, fake_check_output):
            token = getattr(credential, get_token_method)("scope")
            assert token.token == expected_token

            with mock.patch.dict("os.environ", {EnvironmentVariables.AZURE_IDENTITY_DISABLE_MULTITENANTAUTH: "true"}):
                kwargs = {"tenant_id": "un" + expected_tenant}
                if get_token_method == "get_token_info":
                    kwargs = {"options": kwargs}
                token = getattr(credential, get_token_method)("scope", **kwargs)
            assert token.token == expected_token

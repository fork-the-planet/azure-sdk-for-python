# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import os
from typing import Any, List, Union, Dict, Optional
from typing_extensions import Self

import msal

from .msal_client import MsalClient
from .utils import get_default_authority, normalize_authority, resolve_tenant, validate_tenant_id
from .._constants import EnvironmentVariables
from .._persistent_cache import _load_persistent_cache


class MsalCredential:  # pylint: disable=too-many-instance-attributes
    """Base class for credentials wrapping MSAL applications.

    :param str client_id: the principal's client ID
    :param client_credential: client credential data for the application
    :type client_credential: dict
    """

    def __init__(
        self,
        client_id: str,
        client_credential: Optional[Union[str, Dict[str, Any]]] = None,
        *,
        additionally_allowed_tenants: Optional[List[str]] = None,
        authority: Optional[str] = None,
        disable_instance_discovery: Optional[bool] = None,
        tenant_id: Optional[str] = None,
        enable_support_logging: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        self._instance_discovery = None if disable_instance_discovery is None else not disable_instance_discovery
        self._authority = normalize_authority(authority) if authority else get_default_authority()
        self._regional_authority = os.environ.get(EnvironmentVariables.AZURE_REGIONAL_AUTHORITY_NAME)
        if self._regional_authority and self._regional_authority.lower() in ["tryautodetect", "true"]:
            self._regional_authority = msal.ConfidentialClientApplication.ATTEMPT_REGION_DISCOVERY
        self._tenant_id = tenant_id or "organizations"
        validate_tenant_id(self._tenant_id)
        self._client = MsalClient(**kwargs)
        self._client_credential = client_credential
        self._client_id = client_id
        self._enable_support_logging = enable_support_logging
        self._additionally_allowed_tenants = additionally_allowed_tenants or []

        self._client_applications: Dict[str, msal.ClientApplication] = {}
        self._cae_client_applications: Dict[str, msal.ClientApplication] = {}

        self._cache = kwargs.pop("_cache", None)
        self._cae_cache = kwargs.pop("_cae_cache", None)
        if self._cache or self._cae_cache:
            self._custom_cache = True
        else:
            self._custom_cache = False
        self._cache_options = kwargs.pop("cache_persistence_options", None)

        super(MsalCredential, self).__init__()

    def __enter__(self) -> Self:
        self._client.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self._client.__exit__(*args)

    def close(self) -> None:
        """Close the credential's underlying HTTP client and release resources."""
        self.__exit__()

    def _initialize_cache(self, is_cae: bool = False) -> msal.TokenCache:
        if self._cache_options:
            if is_cae:
                self._cae_cache = _load_persistent_cache(self._cache_options, is_cae)
            else:
                self._cache = _load_persistent_cache(self._cache_options, is_cae)
        else:
            if is_cae:
                self._cae_cache = msal.TokenCache()
            else:
                self._cache = msal.TokenCache()

        return self._cae_cache if is_cae else self._cache

    def _get_app(self, **kwargs: Any) -> msal.ClientApplication:
        tenant_id = resolve_tenant(
            self._tenant_id, additionally_allowed_tenants=self._additionally_allowed_tenants, **kwargs
        )

        client_applications_map = self._client_applications
        capabilities = None
        token_cache = self._cache

        app_class = msal.ConfidentialClientApplication if self._client_credential else msal.PublicClientApplication

        if kwargs.get("enable_cae"):
            client_applications_map = self._cae_client_applications
            capabilities = ["CP1"]
            token_cache = self._cae_cache

        if not token_cache:
            token_cache = self._initialize_cache(is_cae=bool(kwargs.get("enable_cae")))

        if tenant_id not in client_applications_map:
            try:
                client_applications_map[tenant_id] = app_class(
                    client_id=self._client_id,
                    client_credential=self._client_credential,
                    client_capabilities=capabilities,
                    authority="{}/{}".format(self._authority, tenant_id),
                    azure_region=self._regional_authority,
                    token_cache=token_cache,
                    http_client=self._client,
                    instance_discovery=self._instance_discovery,
                    enable_pii_log=self._enable_support_logging,
                )
            except ValueError as ex:
                if "invalid_instance" in str(ex):
                    raise ValueError(  # pylint: disable=raise-missing-from
                        f"The authority provided, {self._authority}, is not well-known. If this authority is valid "
                        "and trustworthy, you can disable this check by passing in "
                        "'disable_instance_discovery=True' when constructing the credential."
                    )
                raise

        return client_applications_map[tenant_id]

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        # Remove the non-picklable entries
        del state["_client_applications"]
        del state["_cae_client_applications"]
        if not self._custom_cache:
            del state["_cache"]
            del state["_cae_cache"]
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        # Re-create the unpickable entries
        self._client_applications = {}
        self._cae_client_applications = {}
        if not self._custom_cache:
            self._cache = None
            self._cae_cache = None

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# pylint: disable=docstring-keyword-should-match-keyword-only

from datetime import datetime
from typing import (
    Any, AnyStr, AsyncIterable, cast, Dict, IO, Optional, Union,
    TYPE_CHECKING
)
from urllib.parse import quote, unquote

from typing_extensions import Self

from azure.core.exceptions import HttpResponseError
from azure.core.tracing.decorator_async import distributed_trace_async
from .._data_lake_file_client_helpers import (
    _append_data_options,
    _flush_data_options,
    _upload_options,
)
from .._deserialize import deserialize_file_properties, process_storage_error
from .._models import FileProperties
from .._path_client_helpers import _parse_rename_path
from .._serialize import convert_datetime_to_rfc1123
from .._shared.base_client_async import parse_connection_str
from ..aio._upload_helper import upload_datalake_file
from ._download_async import StorageStreamDownloader
from ._path_client_async import PathClient

if TYPE_CHECKING:
    from azure.core.credentials import AzureNamedKeyCredential, AzureSasCredential
    from azure.core.credentials_async import AsyncTokenCredential
    from .._models import ContentSettings


class DataLakeFileClient(PathClient):
    """A client to interact with the DataLake file, even if the file may not yet exist.

    :param str account_url:
        The URI to the storage account.
    :param file_system_name:
        The file system for the directory or files.
    :type file_system_name: str
    :param file_path:
        The whole file path, so that to interact with a specific file.
        eg. "{directory}/{subdirectory}/{file}"
    :type file_path: str
    :param credential:
        The credentials with which to authenticate. This is optional if the
        account URL already has a SAS token. The value can be a SAS token string,
        an instance of a AzureSasCredential or AzureNamedKeyCredential from azure.core.credentials,
        an account shared access key, or an instance of a TokenCredentials class from azure.identity.
        If the resource URI already contains a SAS token, this will be ignored in favor of an explicit credential
        - except in the case of AzureSasCredential, where the conflicting SAS tokens will raise a ValueError.
        If using an instance of AzureNamedKeyCredential, "name" should be the storage account name, and "key"
        should be the storage account key.
    :type credential:
        ~azure.core.credentials.AzureNamedKeyCredential or
        ~azure.core.credentials.AzureSasCredential or
        ~azure.core.credentials_async.AsyncTokenCredential or
        str or Dict[str, str] or None
    :keyword str api_version:
        The Storage API version to use for requests. Default value is the most recent service version that is
        compatible with the current SDK. Setting to an older version may result in reduced feature compatibility.
    :keyword str audience: The audience to use when requesting tokens for Azure Active Directory
        authentication. Only has an effect when credential is of type AsyncTokenCredential. The value could be
        https://storage.azure.com/ (default) or https://<account>.blob.core.windows.net.

    .. admonition:: Example:

        .. literalinclude:: ../samples/datalake_samples_instantiate_client_async.py
            :start-after: [START instantiate_file_client_from_conn_str]
            :end-before: [END instantiate_file_client_from_conn_str]
            :language: python
            :dedent: 4
            :caption: Creating the DataLakeServiceClient from connection string.
    """

    url: str
    """The full endpoint URL to the file system, including SAS token if used."""
    primary_endpoint: str
    """The full primary endpoint URL."""
    primary_hostname: str
    """The hostname of the primary endpoint."""

    def __init__(
        self, account_url: str,
        file_system_name: str,
        file_path: str,
        credential: Optional[Union[str, Dict[str, str], "AzureNamedKeyCredential", "AzureSasCredential", "AsyncTokenCredential"]] = None,  # pylint: disable=line-too-long
        **kwargs: Any
    ) -> None:
        super(DataLakeFileClient, self).__init__(account_url, file_system_name, path_name=file_path,
                                                 credential=credential, **kwargs)

    @classmethod
    def from_connection_string(
        cls, conn_str: str,
        file_system_name: str,
        file_path: str,
        credential: Optional[Union[str, Dict[str, str], "AzureNamedKeyCredential", "AzureSasCredential", "AsyncTokenCredential"]] = None,  # pylint: disable=line-too-long
        **kwargs: Any
    ) -> Self:
        """
        Create DataLakeFileClient from a Connection String.

        :param str conn_str:
            A connection string to an Azure Storage account.
        :param file_system_name: The name of file system to interact with.
        :type file_system_name: str
        :param str file_path:
            The whole file path, so that to interact with a specific file.
            eg. "{directory}/{subdirectory}/{file}"
        :param credential:
            The credentials with which to authenticate. This is optional if the
            account URL already has a SAS token, or the connection string already has shared
            access key values. The value can be a SAS token string,
            an instance of a AzureSasCredential or AzureNamedKeyCredential from azure.core.credentials,
            an account shared access key, or an instance of a TokenCredentials class from azure.identity.
            Credentials provided here will take precedence over those in the connection string.
            If using an instance of AzureNamedKeyCredential, "name" should be the storage account name, and "key"
            should be the storage account key.
        :type credential:
            ~azure.core.credentials.AzureNamedKeyCredential or
            ~azure.core.credentials.AzureSasCredential or
            ~azure.core.credentials_async.AsyncTokenCredential or
            str or Dict[str, str] or None
        :keyword str audience: The audience to use when requesting tokens for Azure Active Directory
            authentication. Only has an effect when credential is of type AsyncTokenCredential. The value could be
            https://storage.azure.com/ (default) or https://<account>.blob.core.windows.net.
        :returns: A DataLakeFileClient.
        :rtype: ~azure.storage.filedatalake.aio.DataLakeFileClient
        """
        account_url, _, credential = parse_connection_str(conn_str, credential, 'dfs')
        return cls(
            account_url, file_system_name=file_system_name, file_path=file_path,
            credential=credential, **kwargs)

    @distributed_trace_async
    async def create_file(
        self, content_settings: Optional["ContentSettings"] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Dict[str, Union[str, datetime]]:
        """
        Create a new file.

        :param ~azure.storage.filedatalake.ContentSettings content_settings:
            ContentSettings object used to set path properties.
        :param metadata:
            Name-value pairs associated with the file as metadata.
        :type metadata: Optional[Dict[str, str]]
        :keyword lease:
            Required if the file has an active lease. Value can be a DataLakeLeaseClient object
            or the lease ID as a string.
        :paramtype lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword str umask:
            Optional and only valid if Hierarchical Namespace is enabled for the account.
            When creating a file or directory and the parent folder does not have a default ACL,
            the umask restricts the permissions of the file or directory to be created.
            The resulting permission is given by p & ^u, where p is the permission and u is the umask.
            For example, if p is 0777 and u is 0057, then the resulting permission is 0720.
            The default permission is 0777 for a directory and 0666 for a file. The default umask is 0027.
            The umask must be specified in 4-digit octal notation (e.g. 0766).
        :keyword str owner:
            The owner of the file or directory.
        :keyword str group:
            The owning group of the file or directory.
        :keyword str acl:
            Sets POSIX access control rights on files and directories. The value is a
            comma-separated list of access control entries. Each access control entry (ACE) consists of a
            scope, a type, a user or group identifier, and permissions in the format
            "[scope:][type]:[id]:[permissions]".
        :keyword str lease_id:
            Proposed lease ID, in a GUID string format. The DataLake service returns
            400 (Invalid request) if the proposed lease ID is not in the correct format.
        :keyword int lease_duration:
            Specifies the duration of the lease, in seconds, or negative one
            (-1) for a lease that never expires. A non-infinite lease can be
            between 15 and 60 seconds. A lease duration cannot be changed
            using renew or change.
        :keyword expires_on:
            The time to set the file to expiry.
            If the type of expires_on is an int, expiration time will be set
            as the number of milliseconds elapsed from creation time.
            If the type of expires_on is datetime, expiration time will be set
            absolute to the time provided. If no time zone info is provided, this
            will be interpreted as UTC.
        :paramtype expires_on: datetime or int
        :keyword str permissions:
            Optional and only valid if Hierarchical Namespace
            is enabled for the account. Sets POSIX access permissions for the file
            owner, the file owning group, and others. Each class may be granted
            read, write, or execute permission.  The sticky bit is also supported.
            Both symbolic (rwxrw-rw-) and 4-digit octal notation (e.g. 0766) are
            supported.
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword ~azure.storage.filedatalake.CustomerProvidedEncryptionKey cpk:
            Encrypts the data on the service-side with the given key.
            Use of customer-provided keys must be done over HTTPS.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :keyword str encryption_context:
            Specifies the encryption context to set on the file.
        :returns: A dictionary of response headers.
        :rtype: Dict[str, Any]

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_upload_download_async.py
                :start-after: [START create_file]
                :end-before: [END create_file]
                :language: python
                :dedent: 4
                :caption: Create file.
        """
        return await self._create('file', content_settings=content_settings, metadata=metadata, **kwargs)

    @distributed_trace_async
    async def exists(self, **kwargs: Any) -> bool:
        """
        Returns True if a file exists and returns False otherwise.

        :kwarg int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: True if a file exists, False otherwise.
        :rtype: bool
        """
        return await self._exists(**kwargs)

    @distributed_trace_async
    async def delete_file(self, **kwargs: Any) -> None:
        """
        Marks the specified file for deletion.

        :keyword lease:
            Required if the file has an active lease. Value can be a LeaseClient object
            or the lease ID as a string.
        :paramtype lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: A dictionary of response headers.
        :rtype: Dict[str, Any]

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_upload_download_async.py
                :start-after: [START delete_file]
                :end-before: [END delete_file]
                :language: python
                :dedent: 4
                :caption: Delete file.
        """
        return await self._delete(**kwargs)  # type: ignore [return-value]

    @distributed_trace_async
    async def get_file_properties(self, **kwargs: Any) -> FileProperties:
        """Returns all user-defined metadata, standard HTTP properties, and
        system properties for the file. It does not return the content of the file.

        :keyword lease:
            Required if the directory or file has an active lease. Value can be a DataLakeLeaseClient object
            or the lease ID as a string.
        :paramtype lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword ~azure.storage.filedatalake.CustomerProvidedEncryptionKey cpk:
            Decrypts the data on the service-side with the given key.
            Use of customer-provided keys must be done over HTTPS.
            Required if the file was created with a customer-provided key.
        :keyword bool upn:
            If True, the user identity values returned in the x-ms-owner, x-ms-group,
            and x-ms-acl response headers will be transformed from Azure Active Directory Object IDs to User
            Principal Names in the owner, group, and acl fields of
            :class:`~azure.storage.filedatalake.FileProperties`. If False, the values will be returned
            as Azure Active Directory Object IDs. The default value is False. Note that group and application
            Object IDs are not translate because they do not have unique friendly names.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: All user-defined metadata, standard HTTP properties, and system properties for the file.
        :rtype: ~azure.storage.filedatalake.FileProperties

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_upload_download_async.py
                :start-after: [START get_file_properties]
                :end-before: [END get_file_properties]
                :language: python
                :dedent: 4
                :caption: Getting the properties for a file.
        """
        upn = kwargs.pop('upn', None)
        if upn:
            headers = kwargs.pop('headers', {})
            headers['x-ms-upn'] = str(upn)
            kwargs['headers'] = headers
        props = await self._get_path_properties(cls=deserialize_file_properties, **kwargs)
        return cast(FileProperties, props)

    @distributed_trace_async
    async def set_file_expiry(
        self, expiry_options: str,
        expires_on: Optional[Union[datetime, int]] = None,
        **kwargs: Any
    ) -> None:
        """Sets the time a file will expire and be deleted.

        :param str expiry_options:
            Required. Indicates mode of the expiry time.
            Possible values include: 'NeverExpire', 'RelativeToCreation', 'RelativeToNow', 'Absolute'
        :param datetime or int expires_on:
            The time to set the file to expiry.
            When expiry_options is RelativeTo*, expires_on should be an int in milliseconds
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :rtype: None
        """
        expiry_time = None
        if isinstance(expires_on, datetime):
            expiry_time = convert_datetime_to_rfc1123(expires_on)
        elif expires_on is not None:
            expiry_time = str(expires_on)
        await self._datalake_client_for_blob_operation.path.set_expiry(expiry_options, expires_on=expiry_time, **kwargs)

    @distributed_trace_async
    async def upload_data(
        self, data: Union[bytes, str, AsyncIterable[AnyStr], IO[AnyStr]],
        length: Optional[int] = None,
        overwrite: Optional[bool] = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Upload data to a file.

        :param data: Content to be uploaded to file
        :type data: bytes, str, AsyncIterable[AnyStr], or IO[AnyStr]
        :param int length: Size of the data in bytes.
        :param bool overwrite: to overwrite an existing file or not.
        :keyword ~azure.storage.filedatalake.ContentSettings content_settings:
            ContentSettings object used to set path properties.
        :keyword metadata:
            Name-value pairs associated with the blob as metadata.
        :paramtype metadata: Dict[str, str] or None
        :keyword ~azure.storage.filedatalake.DataLakeLeaseClient or str lease:
            Required if the blob has an active lease. Value can be a DataLakeLeaseClient object
            or the lease ID as a string.
        :keyword str umask: Optional and only valid if Hierarchical Namespace is enabled for the account.
            When creating a file or directory and the parent folder does not have a default ACL,
            the umask restricts the permissions of the file or directory to be created.
            The resulting permission is given by p & ^u, where p is the permission and u is the umask.
            For example, if p is 0777 and u is 0057, then the resulting permission is 0720.
            The default permission is 0777 for a directory and 0666 for a file. The default umask is 0027.
            The umask must be specified in 4-digit octal notation (e.g. 0766).
        :keyword str permissions: Optional and only valid if Hierarchical Namespace
         is enabled for the account. Sets POSIX access permissions for the file
         owner, the file owning group, and others. Each class may be granted
         read, write, or execute permission.  The sticky bit is also supported.
         Both symbolic (rwxrw-rw-) and 4-digit octal notation (e.g. 0766) are
         supported.
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword bool validate_content:
            If true, calculates an MD5 hash for each chunk of the file. The storage
            service checks the hash of the content that has arrived with the hash
            that was sent. This is primarily valuable for detecting bitflips on
            the wire if using http instead of https, as https (the default), will
            already validate. Note that this MD5 hash is not stored with the
            blob. Also note that if enabled, the memory-efficient upload algorithm
            will not be used because computing the MD5 hash requires buffering
            entire blocks, and doing so defeats the purpose of the memory-efficient algorithm.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword ~azure.storage.filedatalake.CustomerProvidedEncryptionKey cpk:
            Encrypts the data on the service-side with the given key.
            Use of customer-provided keys must be done over HTTPS.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_. This method may make multiple calls to the service and
            the timeout will apply to each call individually.
        :keyword int max_concurrency:
            Maximum number of parallel connections to use when transferring the file in chunks.
            This option does not affect the underlying connection pool, and may
            require a separate configuration of the connection pool.
        :keyword int chunk_size:
            The maximum chunk size for uploading a file in chunks.
            Defaults to 100*1024*1024, or 100MB.
        :keyword str encryption_context:
            Specifies the encryption context to set on the file.
        :keyword progress_hook:
            A callback to track the progress of a long-running upload. The signature is
            function(current: int, total: int) where current is the number of bytes transferred
            so far, and total is the total size of the download.
        :paramtype progress_hook: ~typing.Callable[[int, Optional[int]], Awaitable[None]]
        :returns: A dictionary of response headers.
        :rtype: Dict[str, Any]
        """
        options = _upload_options(
            data,
            self.scheme,
            self._config,
            self._client.path,
            length=length,
            overwrite=overwrite,
            **kwargs
        )
        return await upload_datalake_file(**options)

    @distributed_trace_async
    async def append_data(
        self, data: Union[bytes, str, AsyncIterable[AnyStr], IO[AnyStr]],
        offset: int,
        length: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Append data to the file.

        :param data: Content to be appended to file
        :type data: bytes, str, AsyncIterable[AnyStr], or IO[AnyStr]
        :param int offset: start position of the data to be appended to.
        :param length: Size of the data in bytes.
        :type length: int or None
        :keyword bool flush:
            If true, will commit the data after it is appended.
        :keyword bool validate_content:
            If true, calculates an MD5 hash of the block content. The storage
            service checks the hash of the content that has arrived
            with the hash that was sent. This is primarily valuable for detecting
            bitflips on the wire if using http instead of https as https (the default)
            will already validate. Note that this MD5 hash is not stored with the
            file.
        :keyword lease_action:
            Used to perform lease operations along with appending data.

            "acquire" - Acquire a lease.
            "auto-renew" - Re-new an existing lease.
            "release" - Release the lease once the operation is complete. Requires `flush=True`.
            "acquire-release" - Acquire a lease and release it once the operations is complete. Requires `flush=True`.
        :paramtype lease_action: Literal["acquire", "auto-renew", "release", "acquire-release"]
        :keyword int lease_duration:
            Valid if `lease_action` is set to "acquire" or "acquire-release".

            Specifies the duration of the lease, in seconds, or negative one
            (-1) for a lease that never expires. A non-infinite lease can be
            between 15 and 60 seconds. A lease duration cannot be changed
            using renew or change. Default is -1 (infinite lease).
        :keyword lease:
            Required if the file has an active lease or if `lease_action` is set to "acquire" or "acquire-release".
            If the file has an existing lease, this will be used to access the file. If acquiring a new lease,
            this will be used as the new lease id.
            Value can be a DataLakeLeaseClient object or the lease ID as a string.
        :paramtype lease: ~azure.storage.filedatalake.DataLakeLeaseClient or str
        :keyword ~azure.storage.filedatalake.CustomerProvidedEncryptionKey cpk:
            Encrypts the data on the service-side with the given key.
            Use of customer-provided keys must be done over HTTPS.
        :returns: A dictionary of response headers.
        :rtype: Dict[str, Any]

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_upload_download_async.py
                :start-after: [START append_data]
                :end-before: [END append_data]
                :language: python
                :dedent: 4
                :caption: Append data to the file.
        """
        options = _append_data_options(
            data=data,
            offset=offset,
            scheme=self.scheme,
            length=length,
            **kwargs)
        try:
            return await self._client.path.append_data(**options)
        except HttpResponseError as error:
            process_storage_error(error)

    @distributed_trace_async
    async def flush_data(
        self, offset: int,
        retain_uncommitted_data: Optional[bool] = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """ Commit the previous appended data.

        :param int offset: offset is equal to the length of the file after commit the
            previous appended data.
        :param bool retain_uncommitted_data: Valid only for flush operations.  If
            "true", uncommitted data is retained after the flush operation
            completes; otherwise, the uncommitted data is deleted after the flush
            operation.  The default is false.  Data at offsets less than the
            specified position are written to the file when flush succeeds, but
            this optional parameter allows data after the flush position to be
            retained for a future flush operation.
        :keyword ~azure.storage.filedatalake.ContentSettings content_settings:
            ContentSettings object used to set path properties.
        :keyword bool close: Azure Storage Events allow applications to receive
            notifications when files change. When Azure Storage Events are
            enabled, a file changed event is raised. This event has a property
            indicating whether this is the final change to distinguish the
            difference between an intermediate flush to a file stream and the
            final close of a file stream. The close query parameter is valid only
            when the action is "flush" and change notifications are enabled. If
            the value of close is "true" and the flush operation completes
            successfully, the service raises a file change notification with a
            property indicating that this is the final update (the file stream has
            been closed). If "false" a change notification is raised indicating
            the file has changed. The default is false. This query parameter is
            set to true by the Hadoop ABFS driver to indicate that the file stream
            has been closed."
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword lease_action:
            Used to perform lease operations along with appending data.

            "acquire" - Acquire a lease.
            "auto-renew" - Re-new an existing lease.
            "release" - Release the lease once the operation is complete.
            "acquire-release" - Acquire a lease and release it once the operations is complete.
        :paramtype lease_action: Literal["acquire", "auto-renew", "release", "acquire-release"]
        :keyword int lease_duration:
            Valid if `lease_action` is set to "acquire" or "acquire-release".

            Specifies the duration of the lease, in seconds, or negative one
            (-1) for a lease that never expires. A non-infinite lease can be
            between 15 and 60 seconds. A lease duration cannot be changed
            using renew or change. Default is -1 (infinite lease).
        :keyword lease:
            Required if the file has an active lease or if `lease_action` is set to "acquire" or "acquire-release".
            If the file has an existing lease, this will be used to access the file. If acquiring a new lease,
            this will be used as the new lease id.
            Value can be a DataLakeLeaseClient object or the lease ID as a string.
        :paramtype lease: ~azure.storage.filedatalake.DataLakeLeaseClient or str
        :keyword ~azure.storage.filedatalake.CustomerProvidedEncryptionKey cpk:
            Encrypts the data on the service-side with the given key.
            Use of customer-provided keys must be done over HTTPS.
        :returns: A dictionary of response headers.
        :rtype: Dict[str, Any]

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_file_system_async.py
                :start-after: [START upload_file_to_file_system]
                :end-before: [END upload_file_to_file_system]
                :language: python
                :dedent: 12
                :caption: Commit the previous appended data.
        """
        options = _flush_data_options(
            offset,
            self.scheme,
            retain_uncommitted_data=retain_uncommitted_data,
            **kwargs
        )
        try:
            return await self._client.path.flush_data(**options)
        except HttpResponseError as error:
            process_storage_error(error)

    @distributed_trace_async
    async def download_file(
        self, offset: Optional[int] = None,
        length: Optional[int] = None,
        **kwargs: Any
    ) -> StorageStreamDownloader:
        """Downloads a file to the StorageStreamDownloader. The readall() method must
        be used to read all the content, or readinto() must be used to download the file into
        a stream. Using chunks() returns an async iterator which allows the user to iterate over the content in chunks.

        :param int offset:
            Start of byte range to use for downloading a section of the file.
            Must be set if length is provided.
        :param int length:
            Number of bytes to read from the stream. This is optional, but
            should be supplied for optimal performance.
        :keyword lease:
            If specified, download only succeeds if the file's lease is active
            and matches this ID. Required if the file has an active lease.
        :paramtype lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword ~azure.storage.filedatalake.CustomerProvidedEncryptionKey cpk:
            Decrypts the data on the service-side with the given key.
            Use of customer-provided keys must be done over HTTPS.
            Required if the file was created with a Customer-Provided Key.
        :keyword int max_concurrency:
            Maximum number of parallel connections to use when transferring the file in chunks.
            This option does not affect the underlying connection pool, and may
            require a separate configuration of the connection pool.
        :keyword progress_hook:
            A callback to track the progress of a long-running download. The signature is
            function(current: int, total: int) where current is the number of bytes transferred
            so far, and total is the total size of the download.
        :paramtype progress_hook: ~typing.Callable[[int, Optional[int]], Awaitable[None]]
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_. This method may make multiple calls to the service and
            the timeout will apply to each call individually.
        :returns: A streaming object (StorageStreamDownloader).
        :rtype: ~azure.storage.filedatalake.aio.StorageStreamDownloader

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_upload_download_async.py
                :start-after: [START read_file]
                :end-before: [END read_file]
                :language: python
                :dedent: 4
                :caption: Return the downloaded data.
        """
        downloader = await self._blob_client.download_blob(offset=offset, length=length, **kwargs)
        return StorageStreamDownloader(downloader)

    @distributed_trace_async
    async def rename_file(self, new_name: str, **kwargs: Any) -> "DataLakeFileClient":
        """
        Rename the source file.

        :param str new_name: the new file name the user want to rename to.
            The value must have the following format: "{filesystem}/{directory}/{subdirectory}/{file}".
        :keyword ~azure.storage.filedatalake.ContentSettings content_settings:
            ContentSettings object used to set path properties.
        :keyword source_lease: A lease ID for the source path. If specified,
            the source path must have an active lease and the lease ID must match.
        :paramtype source_lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword lease:
            Required if the file/directory has an active lease. Value can be a LeaseClient object
            or the lease ID as a string.
        :paramtype lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword ~datetime.datetime source_if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime source_if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str source_etag:
            The source ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions source_match_condition:
            The source match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :return: The renamed file client.
        :rtype: DataLakeFileClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_upload_download_async.py
                :start-after: [START rename_file]
                :end-before: [END rename_file]
                :language: python
                :dedent: 4
                :caption: Rename the source file.
        """
        new_file_system, new_path, new_file_sas = _parse_rename_path(
            new_name, self.file_system_name, self._query_str, self._raw_credential)

        new_file_client = DataLakeFileClient(
            f"{self.scheme}://{self.primary_hostname}", new_file_system, file_path=new_path,
            credential=self._raw_credential or new_file_sas,
            _hosts=self._hosts, _configuration=self._config, _pipeline=self._pipeline,
            _location_mode=self._location_mode)
        await new_file_client._rename_path(  # pylint: disable=protected-access
            f'/{quote(unquote(self.file_system_name))}/{quote(unquote(self.path_name))}{self._query_str}', **kwargs)
        return new_file_client

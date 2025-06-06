# pylint: disable=line-too-long,useless-suppression
# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) Python Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
# pylint: disable=useless-super-delegation

import datetime
from typing import Any, Dict, List, Literal, Mapping, Optional, TYPE_CHECKING, Union, overload

from .. import _model_base
from .._model_base import rest_discriminator, rest_field
from ._enums import SourceType

if TYPE_CHECKING:
    from .. import models as _models


class DateTimeFilter(_model_base.Model):
    """UTC DateTime filter for dependency map visualization apis.

    :ivar start_date_time_utc: Start date time for dependency map visualization query.
    :vartype start_date_time_utc: ~datetime.datetime
    :ivar end_date_time_utc: End date time for dependency map visualization query.
    :vartype end_date_time_utc: ~datetime.datetime
    """

    start_date_time_utc: Optional[datetime.datetime] = rest_field(
        name="startDateTimeUtc", visibility=["read", "create", "update", "delete", "query"], format="rfc3339"
    )
    """Start date time for dependency map visualization query."""
    end_date_time_utc: Optional[datetime.datetime] = rest_field(
        name="endDateTimeUtc", visibility=["read", "create", "update", "delete", "query"], format="rfc3339"
    )
    """End date time for dependency map visualization query."""

    @overload
    def __init__(
        self,
        *,
        start_date_time_utc: Optional[datetime.datetime] = None,
        end_date_time_utc: Optional[datetime.datetime] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class DependencyMapVisualizationFilter(_model_base.Model):
    """Filters for dependency map visualization apis.

    :ivar date_time: DateTime filter.
    :vartype date_time: ~azure.mgmt.dependencymap.models.DateTimeFilter
    :ivar process_name_filter: Process name filter.
    :vartype process_name_filter: ~azure.mgmt.dependencymap.models.ProcessNameFilter
    """

    date_time: Optional["_models.DateTimeFilter"] = rest_field(
        name="dateTime", visibility=["read", "create", "update", "delete", "query"]
    )
    """DateTime filter."""
    process_name_filter: Optional["_models.ProcessNameFilter"] = rest_field(
        name="processNameFilter", visibility=["read", "create", "update", "delete", "query"]
    )
    """Process name filter."""

    @overload
    def __init__(
        self,
        *,
        date_time: Optional["_models.DateTimeFilter"] = None,
        process_name_filter: Optional["_models.ProcessNameFilter"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class Resource(_model_base.Model):
    """Common fields that are returned in the response for all Azure Resource Manager resources.

    :ivar id: Fully qualified resource ID for the resource. Ex -
     /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}.
    :vartype id: str
    :ivar name: The name of the resource.
    :vartype name: str
    :ivar type: The type of the resource. E.g. "Microsoft.Compute/virtualMachines" or
     "Microsoft.Storage/storageAccounts".
    :vartype type: str
    :ivar system_data: Azure Resource Manager metadata containing createdBy and modifiedBy
     information.
    :vartype system_data: ~azure.mgmt.dependencymap.models.SystemData
    """

    id: Optional[str] = rest_field(visibility=["read"])
    """Fully qualified resource ID for the resource. Ex -
     /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}."""
    name: Optional[str] = rest_field(visibility=["read"])
    """The name of the resource."""
    type: Optional[str] = rest_field(visibility=["read"])
    """The type of the resource. E.g. \"Microsoft.Compute/virtualMachines\" or
     \"Microsoft.Storage/storageAccounts\"."""
    system_data: Optional["_models.SystemData"] = rest_field(name="systemData", visibility=["read"])
    """Azure Resource Manager metadata containing createdBy and modifiedBy information."""


class TrackedResource(Resource):
    """The resource model definition for an Azure Resource Manager tracked top level resource which
    has 'tags' and a 'location'.

    :ivar id: Fully qualified resource ID for the resource. Ex -
     /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}.
    :vartype id: str
    :ivar name: The name of the resource.
    :vartype name: str
    :ivar type: The type of the resource. E.g. "Microsoft.Compute/virtualMachines" or
     "Microsoft.Storage/storageAccounts".
    :vartype type: str
    :ivar system_data: Azure Resource Manager metadata containing createdBy and modifiedBy
     information.
    :vartype system_data: ~azure.mgmt.dependencymap.models.SystemData
    :ivar tags: Resource tags.
    :vartype tags: dict[str, str]
    :ivar location: The geo-location where the resource lives. Required.
    :vartype location: str
    """

    tags: Optional[Dict[str, str]] = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Resource tags."""
    location: str = rest_field(visibility=["read", "create"])
    """The geo-location where the resource lives. Required."""

    @overload
    def __init__(
        self,
        *,
        location: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class DiscoverySourceResource(TrackedResource):
    """A Discovery Source resource.

    :ivar id: Fully qualified resource ID for the resource. Ex -
     /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}.
    :vartype id: str
    :ivar name: The name of the resource.
    :vartype name: str
    :ivar type: The type of the resource. E.g. "Microsoft.Compute/virtualMachines" or
     "Microsoft.Storage/storageAccounts".
    :vartype type: str
    :ivar system_data: Azure Resource Manager metadata containing createdBy and modifiedBy
     information.
    :vartype system_data: ~azure.mgmt.dependencymap.models.SystemData
    :ivar tags: Resource tags.
    :vartype tags: dict[str, str]
    :ivar location: The geo-location where the resource lives. Required.
    :vartype location: str
    :ivar properties: The resource-specific properties for this resource.
    :vartype properties: ~azure.mgmt.dependencymap.models.DiscoverySourceResourceProperties
    """

    properties: Optional["_models.DiscoverySourceResourceProperties"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """The resource-specific properties for this resource."""

    @overload
    def __init__(
        self,
        *,
        location: str,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional["_models.DiscoverySourceResourceProperties"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class DiscoverySourceResourceProperties(_model_base.Model):
    """The properties of Discovery Source resource.

    You probably want to use the sub-classes and not this class directly. Known sub-classes are:
    OffAzureDiscoverySourceResourceProperties

    :ivar provisioning_state: Provisioning state of Discovery Source resource. Known values are:
     "Succeeded", "Failed", "Canceled", "Provisioning", "Updating", "Deleting", and "Accepted".
    :vartype provisioning_state: str or ~azure.mgmt.dependencymap.models.ProvisioningState
    :ivar source_type: Source type of Discovery Source resource. Required. "OffAzure"
    :vartype source_type: str or ~azure.mgmt.dependencymap.models.SourceType
    :ivar source_id: Source ArmId of Discovery Source resource. Required.
    :vartype source_id: str
    """

    __mapping__: Dict[str, _model_base.Model] = {}
    provisioning_state: Optional[Union[str, "_models.ProvisioningState"]] = rest_field(
        name="provisioningState", visibility=["read"]
    )
    """Provisioning state of Discovery Source resource. Known values are: \"Succeeded\", \"Failed\",
     \"Canceled\", \"Provisioning\", \"Updating\", \"Deleting\", and \"Accepted\"."""
    source_type: str = rest_discriminator(name="sourceType", visibility=["read", "create"])
    """Source type of Discovery Source resource. Required. \"OffAzure\""""
    source_id: str = rest_field(name="sourceId", visibility=["read", "create"])
    """Source ArmId of Discovery Source resource. Required."""

    @overload
    def __init__(
        self,
        *,
        source_type: str,
        source_id: str,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class DiscoverySourceResourceTagsUpdate(_model_base.Model):
    """The type used for updating tags in DiscoverySourceResource resources.

    :ivar tags: Resource tags.
    :vartype tags: dict[str, str]
    """

    tags: Optional[Dict[str, str]] = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Resource tags."""

    @overload
    def __init__(
        self,
        *,
        tags: Optional[Dict[str, str]] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class ErrorAdditionalInfo(_model_base.Model):
    """The resource management error additional info.

    :ivar type: The additional info type.
    :vartype type: str
    :ivar info: The additional info.
    :vartype info: any
    """

    type: Optional[str] = rest_field(visibility=["read"])
    """The additional info type."""
    info: Optional[Any] = rest_field(visibility=["read"])
    """The additional info."""


class ErrorDetail(_model_base.Model):
    """The error detail.

    :ivar code: The error code.
    :vartype code: str
    :ivar message: The error message.
    :vartype message: str
    :ivar target: The error target.
    :vartype target: str
    :ivar details: The error details.
    :vartype details: list[~azure.mgmt.dependencymap.models.ErrorDetail]
    :ivar additional_info: The error additional info.
    :vartype additional_info: list[~azure.mgmt.dependencymap.models.ErrorAdditionalInfo]
    """

    code: Optional[str] = rest_field(visibility=["read"])
    """The error code."""
    message: Optional[str] = rest_field(visibility=["read"])
    """The error message."""
    target: Optional[str] = rest_field(visibility=["read"])
    """The error target."""
    details: Optional[List["_models.ErrorDetail"]] = rest_field(visibility=["read"])
    """The error details."""
    additional_info: Optional[List["_models.ErrorAdditionalInfo"]] = rest_field(
        name="additionalInfo", visibility=["read"]
    )
    """The error additional info."""


class ErrorResponse(_model_base.Model):
    """Common error response for all Azure Resource Manager APIs to return error details for failed
    operations.

    :ivar error: The error object.
    :vartype error: ~azure.mgmt.dependencymap.models.ErrorDetail
    """

    error: Optional["_models.ErrorDetail"] = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """The error object."""

    @overload
    def __init__(
        self,
        *,
        error: Optional["_models.ErrorDetail"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class ExportDependenciesRequest(_model_base.Model):
    """ExportDependencies request model.

    :ivar focused_machine_id: Machine arm id. Required.
    :vartype focused_machine_id: str
    :ivar filters: Filters for ExportDependencies.
    :vartype filters: ~azure.mgmt.dependencymap.models.DependencyMapVisualizationFilter
    """

    focused_machine_id: str = rest_field(
        name="focusedMachineId", visibility=["read", "create", "update", "delete", "query"]
    )
    """Machine arm id. Required."""
    filters: Optional["_models.DependencyMapVisualizationFilter"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """Filters for ExportDependencies."""

    @overload
    def __init__(
        self,
        *,
        focused_machine_id: str,
        filters: Optional["_models.DependencyMapVisualizationFilter"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class GetConnectionsForProcessOnFocusedMachineRequest(_model_base.Model):  # pylint: disable=name-too-long
    """GetConnectionsForProcessOnFocusedMachine request model.

    :ivar focused_machine_id: Machine arm id. Required.
    :vartype focused_machine_id: str
    :ivar process_id_on_focused_machine: Process id. Required.
    :vartype process_id_on_focused_machine: str
    :ivar filters: Filters for GetProcessNetworkConnections.
    :vartype filters: ~azure.mgmt.dependencymap.models.DependencyMapVisualizationFilter
    """

    focused_machine_id: str = rest_field(
        name="focusedMachineId", visibility=["read", "create", "update", "delete", "query"]
    )
    """Machine arm id. Required."""
    process_id_on_focused_machine: str = rest_field(
        name="processIdOnFocusedMachine", visibility=["read", "create", "update", "delete", "query"]
    )
    """Process id. Required."""
    filters: Optional["_models.DependencyMapVisualizationFilter"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """Filters for GetProcessNetworkConnections."""

    @overload
    def __init__(
        self,
        *,
        focused_machine_id: str,
        process_id_on_focused_machine: str,
        filters: Optional["_models.DependencyMapVisualizationFilter"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class GetConnectionsWithConnectedMachineForFocusedMachineRequest(_model_base.Model):  # pylint: disable=name-too-long
    """GetConnectionsWithConnectedMachineForFocusedMachine request model.

    :ivar focused_machine_id: Source machine arm id. Required.
    :vartype focused_machine_id: str
    :ivar connected_machine_id: Destination machine arm id. Required.
    :vartype connected_machine_id: str
    :ivar filters: Filters for GetNetworkConnectionsBetweenMachines.
    :vartype filters: ~azure.mgmt.dependencymap.models.DependencyMapVisualizationFilter
    """

    focused_machine_id: str = rest_field(
        name="focusedMachineId", visibility=["read", "create", "update", "delete", "query"]
    )
    """Source machine arm id. Required."""
    connected_machine_id: str = rest_field(
        name="connectedMachineId", visibility=["read", "create", "update", "delete", "query"]
    )
    """Destination machine arm id. Required."""
    filters: Optional["_models.DependencyMapVisualizationFilter"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """Filters for GetNetworkConnectionsBetweenMachines."""

    @overload
    def __init__(
        self,
        *,
        focused_machine_id: str,
        connected_machine_id: str,
        filters: Optional["_models.DependencyMapVisualizationFilter"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class GetDependencyViewForFocusedMachineRequest(_model_base.Model):  # pylint: disable=name-too-long
    """GetDependencyViewForFocusedMachine request model.

    :ivar focused_machine_id: Machine arm id. Required.
    :vartype focused_machine_id: str
    :ivar filters: Filters for GetSingleMachineDependencyView.
    :vartype filters: ~azure.mgmt.dependencymap.models.DependencyMapVisualizationFilter
    """

    focused_machine_id: str = rest_field(
        name="focusedMachineId", visibility=["read", "create", "update", "delete", "query"]
    )
    """Machine arm id. Required."""
    filters: Optional["_models.DependencyMapVisualizationFilter"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """Filters for GetSingleMachineDependencyView."""

    @overload
    def __init__(
        self,
        *,
        focused_machine_id: str,
        filters: Optional["_models.DependencyMapVisualizationFilter"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class MapsResource(TrackedResource):
    """A Maps resource.

    :ivar id: Fully qualified resource ID for the resource. Ex -
     /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName}.
    :vartype id: str
    :ivar name: The name of the resource.
    :vartype name: str
    :ivar type: The type of the resource. E.g. "Microsoft.Compute/virtualMachines" or
     "Microsoft.Storage/storageAccounts".
    :vartype type: str
    :ivar system_data: Azure Resource Manager metadata containing createdBy and modifiedBy
     information.
    :vartype system_data: ~azure.mgmt.dependencymap.models.SystemData
    :ivar tags: Resource tags.
    :vartype tags: dict[str, str]
    :ivar location: The geo-location where the resource lives. Required.
    :vartype location: str
    :ivar properties: The resource-specific properties for this resource.
    :vartype properties: ~azure.mgmt.dependencymap.models.MapsResourceProperties
    """

    properties: Optional["_models.MapsResourceProperties"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """The resource-specific properties for this resource."""

    @overload
    def __init__(
        self,
        *,
        location: str,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional["_models.MapsResourceProperties"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class MapsResourceProperties(_model_base.Model):
    """The properties of Maps resource.

    :ivar provisioning_state: Provisioning state of Maps resource. Known values are: "Succeeded",
     "Failed", "Canceled", "Provisioning", "Updating", "Deleting", and "Accepted".
    :vartype provisioning_state: str or ~azure.mgmt.dependencymap.models.ProvisioningState
    """

    provisioning_state: Optional[Union[str, "_models.ProvisioningState"]] = rest_field(
        name="provisioningState", visibility=["read"]
    )
    """Provisioning state of Maps resource. Known values are: \"Succeeded\", \"Failed\", \"Canceled\",
     \"Provisioning\", \"Updating\", \"Deleting\", and \"Accepted\"."""


class MapsResourceTagsUpdate(_model_base.Model):
    """The type used for updating tags in MapsResource resources.

    :ivar tags: Resource tags.
    :vartype tags: dict[str, str]
    """

    tags: Optional[Dict[str, str]] = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Resource tags."""

    @overload
    def __init__(
        self,
        *,
        tags: Optional[Dict[str, str]] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class OffAzureDiscoverySourceResourceProperties(
    DiscoverySourceResourceProperties, discriminator="OffAzure"
):  # pylint: disable=name-too-long
    """OffAzure discovery source resource properties.

    :ivar provisioning_state: Provisioning state of Discovery Source resource. Known values are:
     "Succeeded", "Failed", "Canceled", "Provisioning", "Updating", "Deleting", and "Accepted".
    :vartype provisioning_state: str or ~azure.mgmt.dependencymap.models.ProvisioningState
    :ivar source_id: Source ArmId of Discovery Source resource. Required.
    :vartype source_id: str
    :ivar source_type: OffAzure discovery source type. Required. OffAzure source type
    :vartype source_type: str or ~azure.mgmt.dependencymap.models.OFF_AZURE
    """

    source_type: Literal[SourceType.OFF_AZURE] = rest_discriminator(name="sourceType", visibility=["read", "create", "update", "delete", "query"])  # type: ignore
    """OffAzure discovery source type. Required. OffAzure source type"""

    @overload
    def __init__(
        self,
        *,
        source_id: str,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, source_type=SourceType.OFF_AZURE, **kwargs)


class Operation(_model_base.Model):
    """Details of a REST API operation, returned from the Resource Provider Operations API.

    :ivar name: The name of the operation, as per Resource-Based Access Control (RBAC). Examples:
     "Microsoft.Compute/virtualMachines/write", "Microsoft.Compute/virtualMachines/capture/action".
    :vartype name: str
    :ivar is_data_action: Whether the operation applies to data-plane. This is "true" for
     data-plane operations and "false" for Azure Resource Manager/control-plane operations.
    :vartype is_data_action: bool
    :ivar display: Localized display information for this particular operation.
    :vartype display: ~azure.mgmt.dependencymap.models.OperationDisplay
    :ivar origin: The intended executor of the operation; as in Resource Based Access Control
     (RBAC) and audit logs UX. Default value is "user,system". Known values are: "user", "system",
     and "user,system".
    :vartype origin: str or ~azure.mgmt.dependencymap.models.Origin
    :ivar action_type: Extensible enum. Indicates the action type. "Internal" refers to actions
     that are for internal only APIs. "Internal"
    :vartype action_type: str or ~azure.mgmt.dependencymap.models.ActionType
    """

    name: Optional[str] = rest_field(visibility=["read"])
    """The name of the operation, as per Resource-Based Access Control (RBAC). Examples:
     \"Microsoft.Compute/virtualMachines/write\",
     \"Microsoft.Compute/virtualMachines/capture/action\"."""
    is_data_action: Optional[bool] = rest_field(name="isDataAction", visibility=["read"])
    """Whether the operation applies to data-plane. This is \"true\" for data-plane operations and
     \"false\" for Azure Resource Manager/control-plane operations."""
    display: Optional["_models.OperationDisplay"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """Localized display information for this particular operation."""
    origin: Optional[Union[str, "_models.Origin"]] = rest_field(visibility=["read"])
    """The intended executor of the operation; as in Resource Based Access Control (RBAC) and audit
     logs UX. Default value is \"user,system\". Known values are: \"user\", \"system\", and
     \"user,system\"."""
    action_type: Optional[Union[str, "_models.ActionType"]] = rest_field(name="actionType", visibility=["read"])
    """Extensible enum. Indicates the action type. \"Internal\" refers to actions that are for
     internal only APIs. \"Internal\""""

    @overload
    def __init__(
        self,
        *,
        display: Optional["_models.OperationDisplay"] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class OperationDisplay(_model_base.Model):
    """Localized display information for and operation.

    :ivar provider: The localized friendly form of the resource provider name, e.g. "Microsoft
     Monitoring Insights" or "Microsoft Compute".
    :vartype provider: str
    :ivar resource: The localized friendly name of the resource type related to this operation.
     E.g. "Virtual Machines" or "Job Schedule Collections".
    :vartype resource: str
    :ivar operation: The concise, localized friendly name for the operation; suitable for
     dropdowns. E.g. "Create or Update Virtual Machine", "Restart Virtual Machine".
    :vartype operation: str
    :ivar description: The short, localized friendly description of the operation; suitable for
     tool tips and detailed views.
    :vartype description: str
    """

    provider: Optional[str] = rest_field(visibility=["read"])
    """The localized friendly form of the resource provider name, e.g. \"Microsoft Monitoring
     Insights\" or \"Microsoft Compute\"."""
    resource: Optional[str] = rest_field(visibility=["read"])
    """The localized friendly name of the resource type related to this operation. E.g. \"Virtual
     Machines\" or \"Job Schedule Collections\"."""
    operation: Optional[str] = rest_field(visibility=["read"])
    """The concise, localized friendly name for the operation; suitable for dropdowns. E.g. \"Create
     or Update Virtual Machine\", \"Restart Virtual Machine\"."""
    description: Optional[str] = rest_field(visibility=["read"])
    """The short, localized friendly description of the operation; suitable for tool tips and detailed
     views."""


class ProcessNameFilter(_model_base.Model):
    """Process name filter for dependency map visualization apis.

    :ivar operator: Operator for process name filter. Required. Known values are: "contains" and
     "notContains".
    :vartype operator: str or ~azure.mgmt.dependencymap.models.ProcessNameFilterOperator
    :ivar process_names: List of process names on which the operator should be applied. Required.
    :vartype process_names: list[str]
    """

    operator: Union[str, "_models.ProcessNameFilterOperator"] = rest_field(
        visibility=["read", "create", "update", "delete", "query"]
    )
    """Operator for process name filter. Required. Known values are: \"contains\" and \"notContains\"."""
    process_names: List[str] = rest_field(
        name="processNames", visibility=["read", "create", "update", "delete", "query"]
    )
    """List of process names on which the operator should be applied. Required."""

    @overload
    def __init__(
        self,
        *,
        operator: Union[str, "_models.ProcessNameFilterOperator"],
        process_names: List[str],
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class SystemData(_model_base.Model):
    """Metadata pertaining to creation and last modification of the resource.

    :ivar created_by: The identity that created the resource.
    :vartype created_by: str
    :ivar created_by_type: The type of identity that created the resource. Known values are:
     "User", "Application", "ManagedIdentity", and "Key".
    :vartype created_by_type: str or ~azure.mgmt.dependencymap.models.CreatedByType
    :ivar created_at: The timestamp of resource creation (UTC).
    :vartype created_at: ~datetime.datetime
    :ivar last_modified_by: The identity that last modified the resource.
    :vartype last_modified_by: str
    :ivar last_modified_by_type: The type of identity that last modified the resource. Known values
     are: "User", "Application", "ManagedIdentity", and "Key".
    :vartype last_modified_by_type: str or ~azure.mgmt.dependencymap.models.CreatedByType
    :ivar last_modified_at: The timestamp of resource last modification (UTC).
    :vartype last_modified_at: ~datetime.datetime
    """

    created_by: Optional[str] = rest_field(name="createdBy", visibility=["read", "create", "update", "delete", "query"])
    """The identity that created the resource."""
    created_by_type: Optional[Union[str, "_models.CreatedByType"]] = rest_field(
        name="createdByType", visibility=["read", "create", "update", "delete", "query"]
    )
    """The type of identity that created the resource. Known values are: \"User\", \"Application\",
     \"ManagedIdentity\", and \"Key\"."""
    created_at: Optional[datetime.datetime] = rest_field(
        name="createdAt", visibility=["read", "create", "update", "delete", "query"], format="rfc3339"
    )
    """The timestamp of resource creation (UTC)."""
    last_modified_by: Optional[str] = rest_field(
        name="lastModifiedBy", visibility=["read", "create", "update", "delete", "query"]
    )
    """The identity that last modified the resource."""
    last_modified_by_type: Optional[Union[str, "_models.CreatedByType"]] = rest_field(
        name="lastModifiedByType", visibility=["read", "create", "update", "delete", "query"]
    )
    """The type of identity that last modified the resource. Known values are: \"User\",
     \"Application\", \"ManagedIdentity\", and \"Key\"."""
    last_modified_at: Optional[datetime.datetime] = rest_field(
        name="lastModifiedAt", visibility=["read", "create", "update", "delete", "query"], format="rfc3339"
    )
    """The timestamp of resource last modification (UTC)."""

    @overload
    def __init__(
        self,
        *,
        created_by: Optional[str] = None,
        created_by_type: Optional[Union[str, "_models.CreatedByType"]] = None,
        created_at: Optional[datetime.datetime] = None,
        last_modified_by: Optional[str] = None,
        last_modified_by_type: Optional[Union[str, "_models.CreatedByType"]] = None,
        last_modified_at: Optional[datetime.datetime] = None,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

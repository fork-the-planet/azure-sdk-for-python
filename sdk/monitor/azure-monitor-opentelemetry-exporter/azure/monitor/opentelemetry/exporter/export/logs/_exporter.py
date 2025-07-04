# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import logging
from typing import Optional, Sequence, Any

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.semconv.attributes.exception_attributes import (
    EXCEPTION_ESCAPED,
    EXCEPTION_MESSAGE,
    EXCEPTION_STACKTRACE,
    EXCEPTION_TYPE,
)
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

from azure.monitor.opentelemetry.exporter import _utils
from azure.monitor.opentelemetry.exporter._constants import (
    _EXCEPTION_ENVELOPE_NAME,
    _MESSAGE_ENVELOPE_NAME,
)
from azure.monitor.opentelemetry.exporter._generated.models import (
    ContextTagKeys,
    MessageData,
    MonitorBase,
    TelemetryEventData,
    TelemetryExceptionData,
    TelemetryExceptionDetails,
    TelemetryItem,
)
from azure.monitor.opentelemetry.exporter.export._base import (
    BaseExporter,
    ExportResult,
)
from azure.monitor.opentelemetry.exporter.export.trace import _utils as trace_utils
from azure.monitor.opentelemetry.exporter._constants import (
    _APPLICATION_INSIGHTS_EVENT_MARKER_ATTRIBUTE,
    _MICROSOFT_CUSTOM_EVENT_NAME,
)
from azure.monitor.opentelemetry.exporter.statsbeat._state import (
    get_statsbeat_shutdown,
    get_statsbeat_custom_events_feature_set,
    is_statsbeat_enabled,
    set_statsbeat_custom_events_feature_set,
)

_logger = logging.getLogger(__name__)

_DEFAULT_SPAN_ID = 0
_DEFAULT_TRACE_ID = 0

__all__ = ["AzureMonitorLogExporter"]


class AzureMonitorLogExporter(BaseExporter, LogExporter):
    """Azure Monitor Log exporter for OpenTelemetry."""

    def export(self, batch: Sequence[LogData], **kwargs: Any) -> LogExportResult:  # pylint: disable=unused-argument
        """Export log data.

        :param batch: OpenTelemetry LogData(s) to export.
        :type batch: ~typing.Sequence[~opentelemetry._logs.LogData]
        :return: The result of the export.
        :rtype: ~opentelemetry.sdk._logs.export.LogData
        """
        envelopes = [self._log_to_envelope(log) for log in batch]
        try:
            result = self._transmit(envelopes)
            self._handle_transmit_from_storage(envelopes, result)
            return _get_log_export_result(result)
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Exception occurred while exporting the data.")  # pylint: disable=C4769
            return _get_log_export_result(ExportResult.FAILED_NOT_RETRYABLE)

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """
        if self.storage:
            self.storage.close()

    def _log_to_envelope(self, log_data: LogData) -> TelemetryItem:
        envelope = _convert_log_to_envelope(log_data)
        envelope.instrumentation_key = self._instrumentation_key
        return envelope

    # pylint: disable=docstring-keyword-should-match-keyword-only
    @classmethod
    def from_connection_string(cls, conn_str: str, **kwargs: Any) -> "AzureMonitorLogExporter":
        """
        Create an AzureMonitorLogExporter from a connection string. This is the
        recommended way of instantiation if a connection string is passed in
        explicitly. If a user wants to use a connection string provided by
        environment variable, the constructor of the exporter can be called
        directly.

        :param str conn_str: The connection string to be used for
            authentication.
        :keyword str api_version: The service API version used. Defaults to
            latest.
        :return: an instance of ~AzureMonitorLogExporter
        :rtype: ~azure.monitor.opentelemetry.exporter.AzureMonitorLogExporter
        """
        return cls(connection_string=conn_str, **kwargs)


def _log_data_is_event(log_data: LogData) -> bool:
    log_record = log_data.log_record
    is_event = None
    if log_record.attributes:
        is_event = log_record.attributes.get(_MICROSOFT_CUSTOM_EVENT_NAME) or \
            log_record.attributes.get(_APPLICATION_INSIGHTS_EVENT_MARKER_ATTRIBUTE)  # type: ignore
    return is_event is not None


# pylint: disable=protected-access
def _convert_log_to_envelope(log_data: LogData) -> TelemetryItem:
    log_record = log_data.log_record
    time_stamp = log_record.timestamp if log_record.timestamp is not None else log_record.observed_timestamp
    envelope = _utils._create_telemetry_item(time_stamp)
    envelope.tags.update(_utils._populate_part_a_fields(log_record.resource))  # type: ignore
    envelope.tags[ContextTagKeys.AI_OPERATION_ID] = "{:032x}".format(  # type: ignore
        log_record.trace_id or _DEFAULT_TRACE_ID
    )
    envelope.tags[ContextTagKeys.AI_OPERATION_PARENT_ID] = "{:016x}".format(  # type: ignore
        log_record.span_id or _DEFAULT_SPAN_ID
    )
    if _utils._is_any_synthetic_source(log_record.attributes):
        envelope.tags[ContextTagKeys.AI_OPERATION_SYNTHETIC_SOURCE] = "True"  # type: ignore
    # Special use case: Customers want to be able to set location ip on log records
    location_ip = trace_utils._get_location_ip(log_record.attributes)
    if location_ip:
        envelope.tags[ContextTagKeys.AI_LOCATION_IP] = location_ip  # type: ignore
    properties = _utils._filter_custom_properties(
        log_record.attributes, lambda key, val: not _is_ignored_attribute(key)  # type: ignore
    )
    exc_type = exc_message = stack_trace = None
    if log_record.attributes:
        exc_type = log_record.attributes.get(EXCEPTION_TYPE)
        exc_message = log_record.attributes.get(EXCEPTION_MESSAGE)
        stack_trace = log_record.attributes.get(EXCEPTION_STACKTRACE)
    severity_level = _get_severity_level(log_record.severity_number)

    # Exception telemetry
    if exc_type is not None or exc_message is not None:
        envelope.name = _EXCEPTION_ENVELOPE_NAME
        has_full_stack = stack_trace is not None
        if not exc_type:
            exc_type = "Exception"
        # Log body takes priority for message
        if log_record.body:
            message = _map_body_to_message(log_record.body)
        elif exc_message:
            message = exc_message  # type: ignore
        else:
            message = "Exception"
        exc_details = TelemetryExceptionDetails(
            type_name=str(exc_type)[:1024],  # type: ignore
            message=str(message)[:32768],
            has_full_stack=has_full_stack,
            stack=str(stack_trace)[:32768],
        )
        data = TelemetryExceptionData(  # type: ignore
            severity_level=severity_level,  # type: ignore
            properties=properties,
            exceptions=[exc_details],
        )
        envelope.data = MonitorBase(base_data=data, base_type="ExceptionData")
    elif _log_data_is_event(log_data):  # Event telemetry
        _set_statsbeat_custom_events_feature()
        envelope.name = "Microsoft.ApplicationInsights.Event"
        event_name = ""
        if log_record.attributes.get(_MICROSOFT_CUSTOM_EVENT_NAME):  # type: ignore
            event_name = str(log_record.attributes.get(_MICROSOFT_CUSTOM_EVENT_NAME))  # type: ignore
        else:
            event_name = _map_body_to_message(log_record.body)
        data = TelemetryEventData(  # type: ignore
            name=event_name,
            properties=properties,
        )
        envelope.data = MonitorBase(base_data=data, base_type="EventData")
    else:  # Message telemetry
        envelope.name = _MESSAGE_ENVELOPE_NAME
        # pylint: disable=line-too-long
        # Severity number: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#field-severitynumber
        data = MessageData(  # type: ignore
            message=_map_body_to_message(log_record.body),
            severity_level=severity_level,  # type: ignore
            properties=properties,
        )
        envelope.data = MonitorBase(base_data=data, base_type="MessageData")

    return envelope


def _get_log_export_result(result: ExportResult) -> LogExportResult:
    if result == ExportResult.SUCCESS:
        return LogExportResult.SUCCESS
    return LogExportResult.FAILURE


# pylint: disable=line-too-long
# Common schema: https://github.com/microsoft/common-schema/blob/main/v4.0/Mappings/AzureMonitor-AI.md#exceptionseveritylevel
# SeverityNumber specs: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#field-severitynumber
def _get_severity_level(severity_number: Optional[SeverityNumber]):
    if severity_number is None or severity_number.value < 9:
        return 0
    return int((severity_number.value - 1) / 4 - 1)


def _map_body_to_message(log_body: Any) -> str:
    if not log_body:
        return ""

    if isinstance(log_body, str):
        return log_body[:32768]

    if isinstance(log_body, Exception):
        return str(log_body)[:32768]

    try:
        return json.dumps(log_body)[:32768]
    except:  # pylint: disable=bare-except
        return str(log_body)[:32768]


def _is_ignored_attribute(key: str) -> bool:
    return key in _IGNORED_ATTRS


_IGNORED_ATTRS = frozenset(
    (
        EXCEPTION_TYPE,
        EXCEPTION_MESSAGE,
        EXCEPTION_STACKTRACE,
        EXCEPTION_ESCAPED,
        _APPLICATION_INSIGHTS_EVENT_MARKER_ATTRIBUTE,
        _MICROSOFT_CUSTOM_EVENT_NAME,
    )
)


def _set_statsbeat_custom_events_feature():
    if is_statsbeat_enabled() and not get_statsbeat_shutdown() and not get_statsbeat_custom_events_feature_set():
        set_statsbeat_custom_events_feature_set()

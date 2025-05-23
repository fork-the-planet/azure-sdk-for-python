# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import logging
import threading
import datetime
import warnings
from typing import TYPE_CHECKING, List, Literal, Union, Any, Callable, Optional, Dict, Tuple, overload

from ._client_base import ClientBase
from ._consumer import EventHubConsumer
from ._constants import ALL_PARTITIONS, TransportType
from ._eventprocessor.event_processor import EventProcessor
from ._eventprocessor.common import LoadBalancingStrategy


if TYPE_CHECKING:
    from ssl import SSLContext
    from ._eventprocessor.partition_context import PartitionContext
    from ._common import EventData
    from ._client_base import CredentialTypes
    from ._eventprocessor.common import CloseReason
    from ._eventprocessor.checkpoint_store import CheckpointStore

_LOGGER = logging.getLogger(__name__)


class EventHubConsumerClient(ClientBase):  # pylint: disable=client-accepts-api-version-keyword

    # pylint: disable=client-method-missing-tracing-decorator
    """The EventHubConsumerClient class defines a high level interface for
    receiving events from the Azure Event Hubs service.

    The main goal of `EventHubConsumerClient` is to receive events from all partitions of an EventHub with
    load-balancing and checkpointing.

    When multiple `EventHubConsumerClient` instances are running against the same event hub, consumer group and
    checkpointing location, the partitions will be evenly distributed among them.

    To enable load-balancing and persisted checkpoints, checkpoint_store must be set when creating the
    `EventHubConsumerClient`.
    If a checkpoint store is not provided, the checkpoint will be maintained internally in memory.

    An `EventHubConsumerClient` can also receive from a specific partition when you call its method `receive()` or
    `receive_batch()` and specify the partition_id.
    Load-balancing won't work in single-partition mode. But users can still save checkpoints if the checkpoint_store
    is set.

    :param str fully_qualified_namespace: The fully qualified host name for the Event Hubs namespace.
     The namespace format is: `<yournamespace>.servicebus.windows.net`.
    :param str eventhub_name: The path of the specific Event Hub to connect the client to.
    :param str consumer_group: Receive events from the event hub for this consumer group.
    :param credential: The credential object used for authentication which
     implements a particular interface for getting tokens. It accepts
     :class:`EventHubSharedKeyCredential<azure.eventhub.EventHubSharedKeyCredential>`, or credential objects generated
     by the azure-identity library and objects that implement the `get_token(self, *scopes)` method.
    :type credential: ~azure.core.credentials.TokenCredential or ~azure.core.credentials.AzureSasCredential
     or ~azure.core.credentials.AzureNamedKeyCredential
    :keyword bool logging_enable: Whether to output network trace logs to the logger. Default is `False`.
    :keyword float auth_timeout: The time in seconds to wait for a token to be authorized by the service.
     The default value is 60 seconds. If set to 0, no timeout will be enforced from the client.
    :keyword str user_agent: If specified, this will be added in front of the user agent string.
    :keyword retry_total: The total number of attempts to redo a failed operation when an error occurs.
     Default value is 3. The context of `retry_total` in receiving is special: The `receive` method is implemented
     by a while-loop calling internal receive method in each iteration. In the `receive` case,
     `retry_total` specifies the numbers of retry after error raised by internal receive method in the while-loop.
     If retry attempts are exhausted, the `on_error` callback will be called (if provided) with the error information.
     The failed internal partition consumer will be closed (`on_partition_close` will be called if provided) and
     new internal partition consumer will be created (`on_partition_initialize` will be called if provided) to resume
     receiving.
    :paramtype retry_total: int
    :keyword float retry_backoff_factor: A backoff factor to apply between attempts after the second try
     (most errors are resolved immediately by a second try without a delay).
     In fixed mode, retry policy will always sleep for {backoff factor}.
     In 'exponential' mode, retry policy will sleep for: `{backoff factor} * (2 ** ({number of total retries} - 1))`
     seconds. If the backoff_factor is 0.1, then the retry will sleep
     for [0.0s, 0.2s, 0.4s, ...] between retries. The default value is 0.8.
    :keyword float retry_backoff_max: The maximum back off time. Default value is 120 seconds (2 minutes).
    :keyword retry_mode: The delay behavior between retry attempts. Supported values are 'fixed' or 'exponential',
     where default is 'exponential'.
    :paramtype retry_mode: str
    :keyword float idle_timeout: Timeout, in seconds, after which this client will close the underlying connection
     if there is no further activity. By default the value is None, meaning that the client will not shutdown due to
     inactivity unless initiated by the service.
    :keyword transport_type: The type of transport protocol that will be used for communicating with
     the Event Hubs service. Default is `TransportType.Amqp` in which case port 5671 is used.
     If the port 5671 is unavailable/blocked in the network environment, `TransportType.AmqpOverWebsocket` could
     be used instead which uses port 443 for communication.
    :paramtype transport_type: ~azure.eventhub.TransportType
    :keyword dict[str, str or int] http_proxy: HTTP proxy settings. This must be a dictionary with the following
     keys: `'proxy_hostname'` (str value) and `'proxy_port'` (int value).
     Additionally the following keys may also be present: `'username', 'password'`.
    :keyword checkpoint_store: A manager that stores the partition load-balancing and checkpoint data
     when receiving events. The checkpoint store will be used in both cases of receiving from all partitions
     or a single partition. In the latter case load-balancing does not apply.
     If a checkpoint store is not provided, the checkpoint will be maintained internally
     in memory, and the `EventHubConsumerClient` instance will receive events without load-balancing.
    :paramtype checkpoint_store: ~azure.eventhub.CheckpointStore or None
    :keyword float load_balancing_interval: When load-balancing kicks in. This is the interval, in seconds,
     between two load-balancing evaluations. Default is 30 seconds.
    :keyword float partition_ownership_expiration_interval: A partition ownership will expire after this number
     of seconds. Every load-balancing evaluation will automatically extend the ownership expiration time.
     Default is 6 * load_balancing_interval, i.e. 180 seconds when using the default load_balancing_interval
     of 30 seconds.
    :keyword load_balancing_strategy: When load-balancing kicks in,
     it will use this strategy to claim and balance the partition ownership.
     Use "greedy" or `LoadBalancingStrategy.GREEDY` for the greedy strategy, which, for every
     load-balancing evaluation, will grab as many unclaimed partitions required to balance the load.
     Use "balanced" or `LoadBalancingStrategy.BALANCED` for the balanced strategy, which, for every load-balancing
     evaluation, claims only one partition that is not claimed by other `EventHubConsumerClient`.
     If all partitions of an EventHub are claimed by other `EventHubConsumerClient` and this client has claimed
     too few partitions, this client will steal one partition from other clients for every load-balancing
     evaluation regardless of the load balancing strategy.
     Greedy strategy is used by default.
    :paramtype load_balancing_strategy: str or ~azure.eventhub.LoadBalancingStrategy
    :keyword custom_endpoint_address: The custom endpoint address to use for establishing a connection to
     the Event Hubs service, allowing network requests to be routed through any application gateways or
     other paths needed for the host environment. Default is None.
     Unless specified otherwise, default transport type is TransportType.AmqpOverWebsockets.
     The format would be like "sb://<custom_endpoint_hostname>:<custom_endpoint_port>".
     If port is not specified in the `custom_endpoint_address`, by default port 443 will be used.
    :paramtype custom_endpoint_address: str or None
    :keyword connection_verify: Path to the custom CA_BUNDLE file of the SSL certificate which is used to
     authenticate the identity of the connection endpoint.
     Default is None in which case `certifi.where()` will be used.
    :paramtype connection_verify: str or None
    :keyword ssl_context: The SSLContext object to use in the underlying Pure Python AMQP transport. If specified,
     connection_verify will be ignored.
    :paramtype ssl_context: ssl.SSLContext or None
    :keyword uamqp_transport: Whether to use the `uamqp` library as the underlying transport. The default value is
     False and the Pure Python AMQP library will be used as the underlying transport.
    :paramtype uamqp_transport: bool
    :keyword float socket_timeout: The time in seconds that the underlying socket on the connection should
     wait when sending and receiving data before timing out. The default value is 0.2 for TransportType.Amqp
     and 1 for TransportType.AmqpOverWebsocket. If EventHubsConnectionError errors are occurring due to write
     timing out, a larger than default value may need to be passed in. This is for advanced usage scenarios
     and ordinarily the default value should be sufficient.

    .. admonition:: Example:

        .. literalinclude:: ../samples/sync_samples/sample_code_eventhub.py
            :start-after: [START create_eventhub_consumer_client_sync]
            :end-before: [END create_eventhub_consumer_client_sync]
            :language: python
            :dedent: 4
            :caption: Create a new instance of the EventHubConsumerClient.
    """

    def __init__(
        self,
        fully_qualified_namespace: str,
        eventhub_name: str,
        consumer_group: str,
        credential: "CredentialTypes",
        **kwargs: Any,
    ) -> None:
        # Deprecation of uamqp transport
        if kwargs.get("uamqp_transport"):
            warnings.warn(
                "uAMQP legacy support will be removed in the 5.16.0 minor release. "
                "Please remove the use of `uamqp_transport` keyword argument from the client in order "
                "to use the pure Python AMQP transport. "
                "If you rely on this, please comment on [this issue]"
                "(https://github.com/Azure/azure-sdk-for-python/issues/40347) ",
                DeprecationWarning, stacklevel=2
            )
        self._checkpoint_store = kwargs.pop("checkpoint_store", None)
        self._load_balancing_interval = kwargs.pop("load_balancing_interval", None)
        if self._load_balancing_interval is None:
            self._load_balancing_interval = 30
        self._partition_ownership_expiration_interval = kwargs.pop("partition_ownership_expiration_interval", None)
        if self._partition_ownership_expiration_interval is None:
            self._partition_ownership_expiration_interval = 6 * self._load_balancing_interval
        load_balancing_strategy = kwargs.pop("load_balancing_strategy", None)
        self._load_balancing_strategy = (
            LoadBalancingStrategy(load_balancing_strategy) if load_balancing_strategy else LoadBalancingStrategy.GREEDY
        )
        self._consumer_group = consumer_group
        network_tracing = kwargs.pop("logging_enable", False)
        super(EventHubConsumerClient, self).__init__(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            credential=credential,
            network_tracing=network_tracing,
            **kwargs,
        )
        # consumer auth URI additionally includes consumer group
        self._auth_uri = f"sb://{self._address.hostname}{self._address.path}/consumergroups/{self._consumer_group}"
        self._lock = threading.Lock()
        self._event_processors: Dict[Tuple[str, str], EventProcessor] = {}

    def __enter__(self) -> "EventHubConsumerClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _create_consumer(
        self,
        consumer_group: str,
        partition_id: str,
        event_position: Union[str, int, datetime.datetime],
        on_event_received: Callable[["PartitionContext", "EventData"], None],
        **kwargs: Any,
    ) -> EventHubConsumer:
        owner_level = kwargs.get("owner_level")
        prefetch = kwargs.get("prefetch") or self._config.prefetch
        track_last_enqueued_event_properties = kwargs.get("track_last_enqueued_event_properties", False)
        event_position_inclusive = kwargs.get("event_position_inclusive", False)

        source_url = "amqps://{}{}/ConsumerGroups/{}/Partitions/{}".format(
            self._address.hostname, self._address.path, consumer_group, partition_id
        )
        handler = EventHubConsumer(
            self,
            source_url,
            event_position=event_position,
            event_position_inclusive=event_position_inclusive,
            owner_level=owner_level,
            on_event_received=on_event_received,
            prefetch=prefetch,
            idle_timeout=self._idle_timeout,
            track_last_enqueued_event_properties=track_last_enqueued_event_properties,
            amqp_transport=self._amqp_transport,
        )
        return handler

    @classmethod
    def from_connection_string(
        cls,
        conn_str: str,
        consumer_group: str,
        *,
        eventhub_name: Optional[str] = None,
        logging_enable: bool = False,
        http_proxy: Optional[Dict[str, Union[str, int]]] = None,
        auth_timeout: float = 60,
        user_agent: Optional[str] = None,
        retry_total: int = 3,
        retry_backoff_factor: float = 0.8,
        retry_backoff_max: float = 120,
        retry_mode: Literal["exponential", "fixed"] = "exponential",
        idle_timeout: Optional[float] = None,
        transport_type: TransportType = TransportType.Amqp,
        checkpoint_store: Optional["CheckpointStore"] = None,
        load_balancing_interval: float = 30,
        partition_ownership_expiration_interval: Optional[float] = None,
        load_balancing_strategy: Union[str, LoadBalancingStrategy] = LoadBalancingStrategy.GREEDY,
        custom_endpoint_address: Optional[str] = None,
        connection_verify: Optional[str] = None,
        ssl_context: Optional["SSLContext"] = None,
        uamqp_transport: bool = False,
        **kwargs: Any,
    ) -> "EventHubConsumerClient":
        """Create an EventHubConsumerClient from a connection string.

        :param str conn_str: The connection string of an Event Hub.
        :param str consumer_group: Receive events from the Event Hub for this consumer group.
        :keyword str eventhub_name: The path of the specific Event Hub to connect the client to.
        :keyword bool logging_enable: Whether to output network trace logs to the logger. Default is `False`.
        :keyword float auth_timeout: The time in seconds to wait for a token to be authorized by the service.
         The default value is 60 seconds. If set to 0, no timeout will be enforced from the client.
        :keyword str user_agent: If specified, this will be added in front of the user agent string.
        :keyword retry_total: The total number of attempts to redo a failed operation when an error occurs.
         Default value is 3. The context of `retry_total` in receiving is special: The `receive` method is implemented
         by a while-loop calling internal receive method in each iteration. In the `receive` case,
         `retry_total` specifies the numbers of retry after error raised by internal receive method in the while-loop.
         If retry attempts are exhausted, the `on_error` callback will be called (if provided) with the error
         information. The failed internal partition consumer will be closed (`on_partition_close` will be called
         if provided) and new internal partition consumer will be created (`on_partition_initialize` will be called if
         provided) to resume receiving.
        :paramtype retry_total: int
        :keyword float retry_backoff_factor: A backoff factor to apply between attempts after the second try
         (most errors are resolved immediately by a second try without a delay).
         In fixed mode, retry policy will always sleep for {backoff factor}.
         In 'exponential' mode, retry policy will sleep for: `{backoff factor} * (2 ** ({number of total retries} - 1))`
         seconds. If the backoff_factor is 0.1, then the retry will sleep
         for [0.0s, 0.2s, 0.4s, ...] between retries. The default value is 0.8.
        :keyword float retry_backoff_max: The maximum back off time. Default value is 120 seconds (2 minutes).
        :keyword retry_mode: The delay behavior between retry attempts. Supported values are 'fixed' or 'exponential',
         where default is 'exponential'.
        :paramtype retry_mode: str
        :keyword float idle_timeout: Timeout, in seconds, after which this client will close the underlying connection
         if there is no furthur activity. By default the value is None, meaning that the client will not shutdown due
         to inactivity unless initiated by the service.
        :keyword transport_type: The type of transport protocol that will be used for communicating with
         the Event Hubs service. Default is `TransportType.Amqp` in which case port 5671 is used.
         If the port 5671 is unavailable/blocked in the network environment, `TransportType.AmqpOverWebsocket` could
         be used instead which uses port 443 for communication.
        :paramtype transport_type: ~azure.eventhub.TransportType
        :keyword dict http_proxy: HTTP proxy settings. This must be a dictionary with the following
         keys: `'proxy_hostname'` (str value) and `'proxy_port'` (int value).
         Additionally the following keys may also be present: `'username', 'password'`.
        :keyword checkpoint_store: A manager that stores the partition load-balancing and checkpoint data
         when receiving events. The checkpoint store will be used in both cases of receiving from all partitions
         or a single partition. In the latter case load-balancing does not apply.
         If a checkpoint store is not provided, the checkpoint will be maintained internally
         in memory, and the `EventHubConsumerClient` instance will receive events without load-balancing.
        :paramtype checkpoint_store: ~azure.eventhub.CheckpointStore or None
        :keyword float load_balancing_interval: When load-balancing kicks in. This is the interval, in seconds,
         between two load-balancing evaluations. Default is 10 seconds.
        :keyword float partition_ownership_expiration_interval: A partition ownership will expire after this number
         of seconds. Every load-balancing evaluation will automatically extend the ownership expiration time.
         Default is 6 * load_balancing_interval, i.e. 60 seconds when using the default load_balancing_interval
         of 30 seconds.
        :keyword load_balancing_strategy: When load-balancing kicks in,
         it will use this strategy to claim and balance the partition ownership.
         Use "greedy" or `LoadBalancingStrategy.GREEDY` for the greedy strategy, which, for every
         load-balancing evaluation, will grab as many unclaimed partitions required to balance the load.
         Use "balanced" or `LoadBalancingStrategy.BALANCED` for the balanced strategy, which, for every load-balancing
         evaluation, claims only one partition that is not claimed by other `EventHubConsumerClient`.
         If all partitions of an EventHub are claimed by other `EventHubConsumerClient` and this client has claimed
         too few partitions, this client will steal one partition from other clients for every load-balancing
         evaluation regardless of the load balancing strategy.
         Greedy strategy is used by default.
        :paramtype load_balancing_strategy: str or ~azure.eventhub.LoadBalancingStrategy
        :keyword custom_endpoint_address: The custom endpoint address to use for establishing a connection to
         the Event Hubs service, allowing network requests to be routed through any application gateways or
         other paths needed for the host environment. Default is None.
         Unless specified otherwise, default transport type is TransportType.AmqpOverWebsockets.
         The format would be like "sb://<custom_endpoint_hostname>:<custom_endpoint_port>".
         If port is not specified in the `custom_endpoint_address`, by default port 443 will be used.
        :paramtype custom_endpoint_address: str or None
        :keyword connection_verify: Path to the custom CA_BUNDLE file of the SSL certificate which is used to
         authenticate the identity of the connection endpoint.
         Default is None in which case `certifi.where()` will be used.
        :paramtype connection_verify: str or None
        :keyword ssl_context: The SSLContext object to use in the underlying Pure Python AMQP transport. If specified,
         connection_verify will be ignored.
        :paramtype ssl_context: ssl.SSLContext or None
        :keyword uamqp_transport: Whether to use the `uamqp` library as the underlying transport. The default value is
         False and the Pure Python AMQP library will be used as the underlying transport.
        :paramtype uamqp_transport: bool
        :returns: An EventHubConsumerClient instance.
        :rtype: ~azure.eventhub.EventHubConsumerClient


        .. admonition:: Example:

            .. literalinclude:: ../samples/sync_samples/sample_code_eventhub.py
                :start-after: [START create_eventhub_consumer_client_from_conn_str_sync]
                :end-before: [END create_eventhub_consumer_client_from_conn_str_sync]
                :language: python
                :dedent: 4
                :caption: Create a new instance of the EventHubConsumerClient from connection string.

        """
        constructor_args = cls._from_connection_string(
            conn_str,
            consumer_group=consumer_group,
            eventhub_name=eventhub_name,
            logging_enable=logging_enable,
            http_proxy=http_proxy,
            auth_timeout=auth_timeout,
            user_agent=user_agent,
            retry_total=retry_total,
            retry_backoff_factor=retry_backoff_factor,
            retry_backoff_max=retry_backoff_max,
            retry_mode=retry_mode,
            idle_timeout=idle_timeout,
            transport_type=transport_type,
            checkpoint_store=checkpoint_store,
            load_balancing_interval=load_balancing_interval,
            partition_ownership_expiration_interval=partition_ownership_expiration_interval,
            load_balancing_strategy=load_balancing_strategy,
            custom_endpoint_address=custom_endpoint_address,
            connection_verify=connection_verify,
            ssl_context=ssl_context,
            uamqp_transport=uamqp_transport,
            **kwargs,
        )
        return cls(**constructor_args)

    @overload
    def _receive(
        self, on_event: Callable[["PartitionContext", Optional["EventData"]], None], **kwargs: Any
    ) -> None: ...

    @overload
    def _receive(self, on_event: Callable[["PartitionContext", List["EventData"]], None], **kwargs: Any) -> None: ...

    def _receive(  # pylint:disable=unused-argument
        self,
        on_event: Union[
            Callable[["PartitionContext", Optional["EventData"]], None],
            Callable[["PartitionContext", List["EventData"]], None],
        ],
        *,
        batch: bool = False,
        max_wait_time: Optional[float] = None,
        partition_id: Optional[str] = None,
        max_batch_size: int = 300,
        owner_level: Optional[int] = None,
        prefetch: int = 300,
        track_last_enqueued_event_properties: bool = False,
        starting_position: Optional[Union[str, int, datetime.datetime, Dict[str, Any]]] = None,
        starting_position_inclusive: Union[bool, Dict[str, bool]] = False,
        on_error: Optional[Callable[["PartitionContext", Exception], None]] = None,
        on_partition_initialize: Optional[Callable[["PartitionContext"], None]] = None,
        on_partition_close: Optional[Callable[["PartitionContext", "CloseReason"], None]] = None,
        **kwargs: Any,
    ) -> None:
        with self._lock:
            error: Optional[str] = None
            if (self._consumer_group, ALL_PARTITIONS) in self._event_processors:
                error = (
                    "This consumer client is already receiving events "
                    "from all partitions for consumer group {}.".format(self._consumer_group)
                )
            elif partition_id is None and any(x[0] == self._consumer_group for x in self._event_processors):
                error = "This consumer client is already receiving events " "for consumer group {}.".format(
                    self._consumer_group
                )
            elif (self._consumer_group, partition_id) in self._event_processors:
                error = (
                    "This consumer client is already receiving events "
                    "from partition {} for consumer group {}. ".format(partition_id, self._consumer_group)
                )
            if error:
                _LOGGER.warning(error)
                raise ValueError(error)

            initial_event_position = starting_position if starting_position is not None else "@latest"
            initial_event_position_inclusive = starting_position_inclusive or False
            event_processor = EventProcessor(
                self,
                self._consumer_group,
                on_event,
                batch=batch,
                max_batch_size=max_batch_size,
                partition_id=partition_id,
                checkpoint_store=self._checkpoint_store,
                load_balancing_interval=self._load_balancing_interval,
                load_balancing_strategy=self._load_balancing_strategy,
                partition_ownership_expiration_interval=self._partition_ownership_expiration_interval,
                initial_event_position=initial_event_position,
                initial_event_position_inclusive=initial_event_position_inclusive,
                max_wait_time=max_wait_time,
                owner_level=owner_level,
                prefetch=prefetch,
                track_last_enqueued_event_properties=track_last_enqueued_event_properties,
                on_error=on_error,
                on_partition_initialize=on_partition_initialize,
                on_partition_close=on_partition_close,
            )
            self._event_processors[(self._consumer_group, partition_id or ALL_PARTITIONS)] = event_processor
        try:
            event_processor.start()
        finally:
            event_processor.stop()
            with self._lock:
                try:
                    del self._event_processors[(self._consumer_group, partition_id or ALL_PARTITIONS)]
                except KeyError:
                    pass

    def receive(  # pylint:disable=unused-argument
        self,
        on_event: Callable[["PartitionContext", Optional["EventData"]], None],
        *,
        max_wait_time: Optional[float] = None,
        partition_id: Optional[str] = None,
        owner_level: Optional[int] = None,
        prefetch: int = 300,
        track_last_enqueued_event_properties: bool = False,
        starting_position: Optional[Union[str, int, datetime.datetime, Dict[str, Any]]] = None,
        starting_position_inclusive: Union[bool, Dict[str, bool]] = False,
        on_error: Optional[Callable[["PartitionContext", Exception], None]] = None,
        on_partition_initialize: Optional[Callable[["PartitionContext"], None]] = None,
        on_partition_close: Optional[Callable[["PartitionContext", "CloseReason"], None]] = None,
        **kwargs: Any,
    ) -> None:
        """Receive events from partition(s), with optional load-balancing and checkpointing.

        :param on_event: The callback function for handling a received event. The callback takes two
         parameters: `partition_context` which contains partition context and `event` which is the received event.
         The callback function should be defined like: `on_event(partition_context, event)`.
         For detailed partition context information, please refer to
         :class:`PartitionContext<azure.eventhub.PartitionContext>`.
        :type on_event: callable[~azure.eventhub.PartitionContext, ~azure.eventhub.EventData or None]
        :keyword float max_wait_time: The maximum interval in seconds that the event processor will wait before calling
         the callback. If no events are received within this interval, the `on_event` callback will be called with
         `None`.
         If this value is set to `None` or 0 (the default), the callback will not be called until an event is received.
        :keyword str partition_id: If specified, the client will receive from this partition only.
         Otherwise the client will receive from all partitions.
        :keyword int owner_level: The priority for an exclusive consumer. An exclusive
         consumer will be created if owner_level is set. A consumer with a higher owner_level has higher exclusive
         priority. The owner level is also know as the 'epoch value' of the consumer.
        :keyword int prefetch: The number of events to prefetch from the service
         for processing. Default is 300.
        :keyword bool track_last_enqueued_event_properties: Indicates whether the consumer should request information
         on the last-enqueued event on its associated partition, and track that information as events are received.
         When information about the partitions last-enqueued event is being tracked, each event received from the
         Event Hubs service will carry metadata about the partition. This results in a small amount of additional
         network bandwidth consumption that is generally a favorable trade-off when considered against periodically
         making requests for partition properties using the Event Hub client.
         It is set to `False` by default.
        :keyword starting_position: Start receiving from this event position
         if there is no checkpoint data for a partition. Checkpoint data will be used if available. This can be a
         a dict with partition ID as the key and position as the value for individual partitions, or a single
         value for all partitions. The value type can be str, int or datetime.datetime. Also supported are the
         values "-1" for receiving from the beginning of the stream, and "@latest" for receiving only new events.
         Default value is "@latest".
        :paramtype starting_position: str, int, datetime.datetime or dict[str,any]
        :keyword starting_position_inclusive: Determine whether the given starting_position is inclusive(>=) or
         not (>). True for inclusive and False for exclusive. This can be a dict with partition ID as the key and
         bool as the value indicating whether the starting_position for a specific partition is inclusive or not.
         This can also be a single bool value for all starting_position. The default value is False.
        :paramtype starting_position_inclusive: bool or dict[str,bool]
        :keyword on_error: The callback function that will be called when an error is raised during receiving
         after retry attempts are exhausted, or during the process of load-balancing.
         The callback takes two parameters: `partition_context` which contains partition information
         and `error` being the exception. `partition_context` could be None if the error is raised during
         the process of load-balance. The callback should be defined like: `on_error(partition_context, error)`.
         The `on_error` callback will also be called if an unhandled exception is raised during
         the `on_event` callback.
        :paramtype on_error: callable[[~azure.eventhub.PartitionContext, Exception]]
        :keyword on_partition_initialize: The callback function that will be called after a consumer for a certain
         partition finishes initialization. It would also be called when a new internal partition consumer is created
         to take over the receiving process for a failed and closed internal partition consumer.
         The callback takes a single parameter: `partition_context`
         which contains the partition information. The callback should be defined
         like: `on_partition_initialize(partition_context)`.
        :paramtype on_partition_initialize: callable[[~azure.eventhub.PartitionContext]]
        :keyword on_partition_close: The callback function that will be called after a consumer for a certain
         partition is closed. It would be also called when error is raised during receiving after retry attempts are
         exhausted. The callback takes two parameters: `partition_context` which contains partition
         information and `reason` for the close. The callback should be defined like:
         `on_partition_close(partition_context, reason)`.
         Please refer to :class:`CloseReason<azure.eventhub.CloseReason>` for the various closing reasons.
        :paramtype on_partition_close: callable[[~azure.eventhub.PartitionContext, ~azure.eventhub.CloseReason]]
        :rtype: None

        .. admonition:: Example:

            .. literalinclude:: ../samples/sync_samples/sample_code_eventhub.py
                :start-after: [START eventhub_consumer_client_receive_sync]
                :end-before: [END eventhub_consumer_client_receive_sync]
                :language: python
                :dedent: 4
                :caption: Receive events from the EventHub.
        """
        self._receive(
            on_event,
            batch=False,
            max_batch_size=1,
            max_wait_time=max_wait_time,
            partition_id=partition_id,
            owner_level=owner_level,
            prefetch=prefetch,
            track_last_enqueued_event_properties=track_last_enqueued_event_properties,
            starting_position=starting_position,
            starting_position_inclusive=starting_position_inclusive,
            on_error=on_error,
            on_partition_initialize=on_partition_initialize,
            on_partition_close=on_partition_close,
        )

    def receive_batch(
        self,
        on_event_batch: Callable[["PartitionContext", List["EventData"]], None],
        *,
        max_batch_size: int = 300,
        max_wait_time: Optional[float] = None,
        partition_id: Optional[str] = None,
        owner_level: Optional[int] = None,
        prefetch: int = 300,
        track_last_enqueued_event_properties: bool = False,
        starting_position: Optional[Union[str, int, datetime.datetime, Dict[str, Any]]] = None,
        starting_position_inclusive: Union[bool, Dict[str, bool]] = False,
        on_error: Optional[Callable[["PartitionContext", Exception], None]] = None,
        on_partition_initialize: Optional[Callable[["PartitionContext"], None]] = None,
        on_partition_close: Optional[Callable[["PartitionContext", "CloseReason"], None]] = None,
        **kwargs: Any,
    ) -> None:
        """Receive events from partition(s), with optional load-balancing and checkpointing.

        :param on_event_batch: The callback function for handling a batch of received events. The callback takes two
         parameters: `partition_context` which contains partition context and `event_batch`, which is the received
         events. The callback function should be defined like: `on_event_batch(partition_context, event_batch)`.
         `event_batch` could be an empty list if `max_wait_time` is not None nor 0 and no event is received
         after `max_wait_time`.
         For detailed partition context information, please refer to
         :class:`PartitionContext<azure.eventhub.PartitionContext>`.
        :type on_event_batch: callable[~azure.eventhub.PartitionContext, list[~azure.eventhub.EventData]]
        :keyword int max_batch_size: The maximum number of events in a batch passed to callback `on_event_batch`.
         If the actual received number of events is larger than `max_batch_size`, the received events are divided into
         batches and call the callback for each batch with up to `max_batch_size` events.
        :keyword float max_wait_time: The maximum interval in seconds that the event processor will wait before
         calling the callback.
         If no events are received within this interval, the `on_event_batch` callback will be called
         with an empty list.
        :keyword str partition_id: If specified, the client will receive from this partition only.
         Otherwise the client will receive from all partitions.
        :keyword int owner_level: The priority for an exclusive consumer. An exclusive
         consumer will be created if owner_level is set. A consumer with a higher owner_level has higher exclusive
         priority. The owner level is also know as the 'epoch value' of the consumer.
        :keyword int prefetch: The number of events to prefetch from the service
         for processing. Default is 300.
        :keyword bool track_last_enqueued_event_properties: Indicates whether the consumer should request information
         on the last-enqueued event on its associated partition, and track that information as events are received.
         When information about the partitions last-enqueued event is being tracked, each event received from the
         Event Hubs service will carry metadata about the partition. This results in a small amount of additional
         network bandwidth consumption that is generally a favorable trade-off when considered against periodically
         making requests for partition properties using the Event Hub client.
         It is set to `False` by default.
        :keyword starting_position: Start receiving from this event position
         if there is no checkpoint data for a partition. Checkpoint data will be used if available. This can be a
         a dict with partition ID as the key and position as the value for individual partitions, or a single
         value for all partitions. The value type can be str, int or datetime.datetime. Also supported are the
         values "-1" for receiving from the beginning of the stream, and "@latest" for receiving only new events.
         Default value is "@latest".
        :paramtype starting_position: str, int, datetime.datetime or dict[str,any]
        :keyword starting_position_inclusive: Determine whether the given starting_position is inclusive(>=) or
         not (>). True for inclusive and False for exclusive. This can be a dict with partition ID as the key and
         bool as the value indicating whether the starting_position for a specific partition is inclusive or not.
         This can also be a single bool value for all starting_position. The default value is False.
        :paramtype starting_position_inclusive: bool or dict[str,bool]
        :keyword on_error: The callback function that will be called when an error is raised during receiving
         after retry attempts are exhausted, or during the process of load-balancing.
         The callback takes two parameters: `partition_context` which contains partition information
         and `error` being the exception. `partition_context` could be None if the error is raised during
         the process of load-balance. The callback should be defined like: `on_error(partition_context, error)`.
         The `on_error` callback will also be called if an unhandled exception is raised during
         the `on_event` callback.
        :paramtype on_error: callable[[~azure.eventhub.PartitionContext, Exception]]
        :keyword on_partition_initialize: The callback function that will be called after a consumer for a certain
         partition finishes initialization. It would also be called when a new internal partition consumer is created
         to take over the receiving process for a failed and closed internal partition consumer.
         The callback takes a single parameter: `partition_context`
         which contains the partition information. The callback should be defined
         like: `on_partition_initialize(partition_context)`.
        :paramtype on_partition_initialize: callable[[~azure.eventhub.PartitionContext]]
        :keyword on_partition_close: The callback function that will be called after a consumer for a certain
         partition is closed. It would be also called when error is raised during receiving after retry attempts are
         exhausted. The callback takes two parameters: `partition_context` which contains partition
         information and `reason` for the close. The callback should be defined like:
         `on_partition_close(partition_context, reason)`.
         Please refer to :class:`CloseReason<azure.eventhub.CloseReason>` for the various closing reasons.
        :paramtype on_partition_close: callable[[~azure.eventhub.PartitionContext, ~azure.eventhub.CloseReason]]
        :rtype: None

        .. admonition:: Example:

            .. literalinclude:: ../samples/sync_samples/sample_code_eventhub.py
                :start-after: [START eventhub_consumer_client_receive_batch_sync]
                :end-before: [END eventhub_consumer_client_receive_batch_sync]
                :language: python
                :dedent: 4
                :caption: Receive events in batches from the EventHub.
        """
        self._receive(
            on_event_batch,
            batch=True,
            max_batch_size=max_batch_size,
            max_wait_time=max_wait_time,
            partition_id=partition_id,
            owner_level=owner_level,
            prefetch=prefetch,
            track_last_enqueued_event_properties=track_last_enqueued_event_properties,
            starting_position=starting_position,
            starting_position_inclusive=starting_position_inclusive,
            on_error=on_error,
            on_partition_initialize=on_partition_initialize,
            on_partition_close=on_partition_close,
            **kwargs,
        )

    def get_eventhub_properties(self) -> Dict[str, Any]:
        """Get properties of the Event Hub.

        Keys in the returned dictionary include:

            - `eventhub_name` (str)
            - `created_at` (UTC datetime.datetime)
            - `partition_ids` (list[str])

        :return: A dictionary containing information about the Event Hub.
        :rtype: dict[str, any]
        :raises: :class:`EventHubError<azure.eventhub.exceptions.EventHubError>`
        """
        return super(EventHubConsumerClient, self)._get_eventhub_properties()

    def get_partition_ids(self) -> List[str]:
        """Get partition IDs of the Event Hub.

        :return: A list of partition IDs.
        :rtype: list[str]
        :raises: :class:`EventHubError<azure.eventhub.exceptions.EventHubError>`
        """
        return super(EventHubConsumerClient, self)._get_partition_ids()

    def get_partition_properties(self, partition_id: str) -> Dict[str, Any]:
        """Get properties of the specified partition.

        Keys in the properties dictionary include:

            - `eventhub_name` (str)
            - `id` (str)
            - `beginning_sequence_number` (int)
            - `last_enqueued_sequence_number` (int)
            - `last_enqueued_offset` (str)
            - `last_enqueued_time_utc` (UTC datetime.datetime)
            - `is_empty` (bool)

        :param partition_id: The target partition ID.
        :type partition_id: str
        :return: A dictionary containing partition properties.
        :rtype: dict[str, any]
        :raises: :class:`EventHubError<azure.eventhub.exceptions.EventHubError>`
        """
        return super(EventHubConsumerClient, self)._get_partition_properties(partition_id)

    def close(self) -> None:
        """Stop retrieving events from the Event Hub and close the underlying AMQP connection and links.

        :rtype: None

        .. admonition:: Example:

            .. literalinclude:: ../samples/sync_samples/sample_code_eventhub.py
                :start-after: [START eventhub_consumer_client_close_sync]
                :end-before: [END eventhub_consumer_client_close_sync]
                :language: python
                :dedent: 4
                :caption: Close down the client.

        """
        with self._lock:
            for processor in self._event_processors.values():
                processor.stop()
            self._event_processors = {}
        super(EventHubConsumerClient, self)._close()

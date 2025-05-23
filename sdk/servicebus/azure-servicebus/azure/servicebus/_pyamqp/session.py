# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from __future__ import annotations
import uuid
import logging
import time
from typing import Union, Optional

from .constants import ConnectionState, SessionState, SessionTransferState, Role
from .sender import SenderLink
from .receiver import ReceiverLink
from .management_link import ManagementLink
from .performatives import (
    BeginFrame,
    EndFrame,
    FlowFrame,
    TransferFrame,
    DispositionFrame,
)
from .error import AMQPError, ErrorCondition
from ._encode import encode_frame

_LOGGER = logging.getLogger(__name__)


class Session(object):  # pylint: disable=too-many-instance-attributes
    """
    :param int remote_channel: The remote channel for this Session.
    :param int next_outgoing_id: The transfer-id of the first transfer id the sender will send.
    :param int incoming_window: The initial incoming-window of the sender.
    :param int outgoing_window: The initial outgoing-window of the sender.
    :param int handle_max: The maximum handle value that may be used on the Session.
    :param list(str) offered_capabilities: The extension capabilities the sender supports.
    :param list(str) desired_capabilities: The extension capabilities the sender may use if the receiver supports
    :param dict properties: Session properties.
    """

    def __init__(self, connection, channel, **kwargs):
        self.name = kwargs.pop("name", None) or str(uuid.uuid4())
        self.state = SessionState.UNMAPPED
        self.handle_max = kwargs.get("handle_max", 4294967295)
        self.properties = kwargs.pop("properties", None)
        self.remote_properties = None
        self.channel = channel
        self.remote_channel = None
        self.next_outgoing_id = kwargs.pop("next_outgoing_id", 0)
        self.next_incoming_id = None
        self.incoming_window = kwargs.pop("incoming_window", 1)
        self.outgoing_window = kwargs.pop("outgoing_window", 1)
        self.target_incoming_window = self.incoming_window
        self.remote_incoming_window = 0
        self.remote_outgoing_window = 0
        self.offered_capabilities = None
        self.desired_capabilities = kwargs.pop("desired_capabilities", None)

        self.allow_pipelined_open = kwargs.pop("allow_pipelined_open", True)
        self.idle_wait_time = kwargs.get("idle_wait_time", 0.1)
        self.network_trace = kwargs["network_trace"]
        self.network_trace_params = kwargs["network_trace_params"]
        self.network_trace_params["amqpSession"] = self.name

        self.links = {}
        self._connection = connection
        self._output_handles = {}
        self._input_handles = {}

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, *args):
        self.end()

    @classmethod
    def from_incoming_frame(cls, connection, channel):
        # TODO: check session_create_from_endpoint in C lib
        new_session = cls(connection, channel)
        return new_session

    def _set_state(self, new_state: SessionState) -> None:
        """Update the session state.
        :param ~pyamqp.constants.SessionState new_state: The new state to set.
        """
        if new_state is None:
            return
        previous_state = self.state
        self.state = new_state
        _LOGGER.info(
            "Session state changed: %r -> %r",
            previous_state,
            new_state,
            extra=self.network_trace_params,
        )
        for link in self.links.values():
            link._on_session_state_change()  # pylint: disable=protected-access

    def _on_connection_state_change(self):
        if self._connection.state in [ConnectionState.CLOSE_RCVD, ConnectionState.END]:
            if self.state not in [SessionState.DISCARDING, SessionState.UNMAPPED]:
                self._set_state(SessionState.DISCARDING)

    def _get_next_output_handle(self) -> int:
        """Get the next available outgoing handle number within the max handle limit.

        :raises ValueError: If maximum handle has been reached.
        :returns: The next available outgoing handle number.
        :rtype: int
        """
        if len(self._output_handles) >= self.handle_max:
            raise ValueError("Maximum number of handles ({}) has been reached.".format(self.handle_max))
        next_handle = next(i for i in range(1, self.handle_max) if i not in self._output_handles)
        return next_handle

    def _outgoing_begin(self):
        begin_frame = BeginFrame(
            remote_channel=self.remote_channel if self.state == SessionState.BEGIN_RCVD else None,
            next_outgoing_id=self.next_outgoing_id,
            outgoing_window=self.outgoing_window,
            incoming_window=self.incoming_window,
            handle_max=self.handle_max,
            offered_capabilities=self.offered_capabilities if self.state == SessionState.BEGIN_RCVD else None,
            desired_capabilities=self.desired_capabilities if self.state == SessionState.UNMAPPED else None,
            properties=self.properties,
        )
        if self.network_trace:
            _LOGGER.debug("-> %r", begin_frame, extra=self.network_trace_params)
        self._connection._process_outgoing_frame(self.channel, begin_frame)  # pylint: disable=protected-access

    def _incoming_begin(self, frame):
        if self.network_trace:
            _LOGGER.debug("<- %r", BeginFrame(*frame), extra=self.network_trace_params)
        self.handle_max = frame[4]  # handle_max
        self.next_incoming_id = frame[1]  # next_outgoing_id
        self.remote_incoming_window = frame[2]  # incoming_window
        self.remote_outgoing_window = frame[3]  # outgoing_window
        self.remote_properties = frame[7]  # incoming map of properties about the session
        if self.state == SessionState.BEGIN_SENT:
            self.remote_channel = frame[0]  # remote_channel
            self._set_state(SessionState.MAPPED)
        elif self.state == SessionState.UNMAPPED:
            self._set_state(SessionState.BEGIN_RCVD)
            self._outgoing_begin()
            self._set_state(SessionState.MAPPED)

    def _outgoing_end(self, error=None):
        end_frame = EndFrame(error=error)
        if self.network_trace:
            _LOGGER.debug("-> %r", end_frame, extra=self.network_trace_params)
        self._connection._process_outgoing_frame(self.channel, end_frame)  # pylint: disable=protected-access

    def _incoming_end(self, frame):
        if self.network_trace:
            _LOGGER.debug("<- %r", EndFrame(*frame), extra=self.network_trace_params)
        if self.state not in [
            SessionState.END_RCVD,
            SessionState.END_SENT,
            SessionState.DISCARDING,
        ]:
            self._set_state(SessionState.END_RCVD)
            for _, link in self.links.items():
                link.detach()
            # TODO: handling error
            self._outgoing_end()
        self._set_state(SessionState.UNMAPPED)

    def _outgoing_attach(self, frame):
        self._connection._process_outgoing_frame(self.channel, frame)  # pylint: disable=protected-access

    def _incoming_attach(self, frame):
        try:
            self._input_handles[frame[1]] = self.links[frame[0].decode("utf-8")]  # name and handle
            self._input_handles[frame[1]]._incoming_attach(frame)  # pylint: disable=protected-access
        except KeyError:
            try:
                outgoing_handle = self._get_next_output_handle()
            except ValueError:
                _LOGGER.error(
                    "Unable to attach new link - cannot allocate more handles.", extra=self.network_trace_params
                )
                # detach the link that would have been set.
                self.links[frame[0].decode("utf-8")].detach(
                    error=AMQPError(
                        condition=ErrorCondition.LinkDetachForced,
                        description="""Cannot allocate more handles, """
                        """the max number of handles is {}. Detaching link""".format(self.handle_max),
                        info=None,
                    )
                )
                return
            if frame[2] == Role.Sender:  # role
                new_link = ReceiverLink.from_incoming_frame(self, outgoing_handle, frame)
            else:
                new_link = SenderLink.from_incoming_frame(self, outgoing_handle, frame)
            new_link._incoming_attach(frame)  # pylint: disable=protected-access
            self.links[frame[0]] = new_link
            self._output_handles[outgoing_handle] = new_link
            self._input_handles[frame[1]] = new_link
        except ValueError as e:
            # Reject Link
            _LOGGER.debug("Unable to attach new link: %r", e, extra=self.network_trace_params)
            self._input_handles[frame[1]].detach()

    def _outgoing_flow(self, frame=None):
        link_flow = frame or {}
        link_flow.update(
            {
                "next_incoming_id": self.next_incoming_id,
                "incoming_window": self.incoming_window,
                "next_outgoing_id": self.next_outgoing_id,
                "outgoing_window": self.outgoing_window,
            }
        )
        flow_frame = FlowFrame(**link_flow)
        if self.network_trace:
            _LOGGER.debug("-> %r", flow_frame, extra=self.network_trace_params)
        self._connection._process_outgoing_frame(self.channel, flow_frame)  # pylint: disable=protected-access

    def _incoming_flow(self, frame):
        if self.network_trace:
            _LOGGER.debug("<- %r", FlowFrame(*frame), extra=self.network_trace_params)
        self.next_incoming_id = frame[2]  # next_outgoing_id
        remote_incoming_id = frame[0] or self.next_outgoing_id  #  next_incoming_id  TODO "initial-outgoing-id"
        self.remote_incoming_window = remote_incoming_id + frame[1] - self.next_outgoing_id  # incoming_window
        self.remote_outgoing_window = frame[3]  # outgoing_window
        if frame[4] is not None:  # handle
            self._input_handles[frame[4]]._incoming_flow(frame)  # pylint: disable=protected-access
        else:
            for link in self._output_handles.values():
                if self.remote_incoming_window > 0 and not link._is_closed:  # pylint: disable=protected-access
                    link._incoming_flow(frame)  # pylint: disable=protected-access

    def _outgoing_transfer(self, delivery, network_trace_params):
        if self.state != SessionState.MAPPED:
            delivery.transfer_state = SessionTransferState.ERROR
        if self.remote_incoming_window <= 0:
            delivery.transfer_state = SessionTransferState.BUSY
        else:
            payload = delivery.frame["payload"]
            payload_size = len(payload)

            delivery.frame["delivery_id"] = self.next_outgoing_id
            # calculate the transfer frame encoding size excluding the payload
            delivery.frame["payload"] = b""
            # TODO: encoding a frame would be expensive, we might want to improve depending on the perf test results
            encoded_frame = encode_frame(TransferFrame(**delivery.frame))[1]
            transfer_overhead_size = len(encoded_frame)

            # available size for payload per frame is calculated as following:
            # remote max frame size - transfer overhead (calculated) - header (8 bytes)
            available_frame_size = (
                self._connection._remote_max_frame_size - transfer_overhead_size - 8  # pylint: disable=protected-access
            )

            start_idx = 0
            remaining_payload_cnt = payload_size
            # encode n-1 frames if payload_size > available_frame_size
            while remaining_payload_cnt > available_frame_size:
                tmp_delivery_frame = {
                    "handle": delivery.frame["handle"],
                    "delivery_tag": delivery.frame["delivery_tag"],
                    "message_format": delivery.frame["message_format"],
                    "settled": delivery.frame["settled"],
                    "more": True,
                    "rcv_settle_mode": delivery.frame["rcv_settle_mode"],
                    "state": delivery.frame["state"],
                    "resume": delivery.frame["resume"],
                    "aborted": delivery.frame["aborted"],
                    "batchable": delivery.frame["batchable"],
                    "delivery_id": self.next_outgoing_id,
                }
                if network_trace_params:
                    # We determine the logging for the outgoing Transfer frames based on the source
                    # Link configuration rather than the Session, because it's only at the Session
                    # level that we can determine how many outgoing frames are needed and their
                    # delivery IDs.
                    # TODO: Obscuring the payload for now to investigate the potential for leaks.
                    _LOGGER.debug(
                        "-> %r", TransferFrame(payload=b"***", **tmp_delivery_frame), extra=network_trace_params
                    )
                self._connection._process_outgoing_frame(  # pylint: disable=protected-access
                    self.channel,
                    TransferFrame(payload=payload[start_idx : start_idx + available_frame_size], **tmp_delivery_frame),
                )
                start_idx += available_frame_size
                remaining_payload_cnt -= available_frame_size

            # encode the last frame
            tmp_delivery_frame = {
                "handle": delivery.frame["handle"],
                "delivery_tag": delivery.frame["delivery_tag"],
                "message_format": delivery.frame["message_format"],
                "settled": delivery.frame["settled"],
                "more": False,
                "rcv_settle_mode": delivery.frame["rcv_settle_mode"],
                "state": delivery.frame["state"],
                "resume": delivery.frame["resume"],
                "aborted": delivery.frame["aborted"],
                "batchable": delivery.frame["batchable"],
                "delivery_id": self.next_outgoing_id,
            }
            if network_trace_params:
                # We determine the logging for the outgoing Transfer frames based on the source
                # Link configuration rather than the Session, because it's only at the Session
                # level that we can determine how many outgoing frames are needed and their
                # delivery IDs.
                # TODO: Obscuring the payload for now to investigate the potential for leaks.
                _LOGGER.debug("-> %r", TransferFrame(payload=b"***", **tmp_delivery_frame), extra=network_trace_params)
            self._connection._process_outgoing_frame(  # pylint: disable=protected-access
                self.channel, TransferFrame(payload=payload[start_idx:], **tmp_delivery_frame)
            )
            self.next_outgoing_id += 1
            self.remote_incoming_window -= 1
            self.outgoing_window -= 1
            # TODO: We should probably handle an error at the connection and update state accordingly
            delivery.transfer_state = SessionTransferState.OKAY

    def _incoming_transfer(self, frame):
        # TODO: should this be only if more=False?
        self.next_incoming_id += 1
        self.remote_outgoing_window -= 1
        self.incoming_window -= 1
        try:
            self._input_handles[frame[0]]._incoming_transfer(frame)  # pylint: disable=protected-access
        except KeyError:
            _LOGGER.error(
                "Received Transfer frame on unattached link. Ending session.", extra=self.network_trace_params
            )
            self._set_state(SessionState.DISCARDING)
            self.end(
                error=AMQPError(
                    condition=ErrorCondition.SessionUnattachedHandle,
                    description="""Invalid handle reference in received frame: """
                    """Handle is not currently associated with an attached link""",
                )
            )
            return
        if self.incoming_window == 0:
            self.incoming_window = self.target_incoming_window
            self._outgoing_flow()

    def _outgoing_disposition(self, frame):
        self._connection._process_outgoing_frame(self.channel, frame)  # pylint: disable=protected-access

    def _incoming_disposition(self, frame):
        if self.network_trace:
            _LOGGER.debug("<- %r", DispositionFrame(*frame), extra=self.network_trace_params)
        for link in self._input_handles.values():
            link._incoming_disposition(frame)  # pylint: disable=protected-access

    def _outgoing_detach(self, frame):
        self._connection._process_outgoing_frame(self.channel, frame)  # pylint: disable=protected-access

    def _incoming_detach(self, frame):
        try:
            link = self._input_handles[frame[0]]  # handle
            link._incoming_detach(frame)  # pylint: disable=protected-access
            # if link._is_closed:  TODO
            #     self.links.pop(link.name, None)
            #     self._input_handles.pop(link.remote_handle, None)
            #     self._output_handles.pop(link.handle, None)
        except KeyError:
            self._set_state(SessionState.DISCARDING)
            self._connection.close(
                error=AMQPError(
                    condition=ErrorCondition.SessionUnattachedHandle,
                    description="""Invalid handle reference in received frame: """
                    """Handle is not currently associated with an attached link""",
                )
            )

    def _wait_for_response(self, wait: Union[bool, float], end_state: SessionState) -> None:
        if wait is True:
            self._connection.listen(wait=False)
            while self.state != end_state:
                time.sleep(self.idle_wait_time)
                self._connection.listen(wait=False)
        elif wait:
            self._connection.listen(wait=False)
            timeout = time.time() + wait
            while self.state != end_state:
                if time.time() >= timeout:
                    break
                time.sleep(self.idle_wait_time)
                self._connection.listen(wait=False)

    def begin(self, wait=False):
        self._outgoing_begin()
        self._set_state(SessionState.BEGIN_SENT)
        if wait:
            self._wait_for_response(wait, SessionState.BEGIN_SENT)
        elif not self.allow_pipelined_open:
            raise ValueError("Connection has been configured to not allow piplined-open. Please set 'wait' parameter.")

    def end(self, error: Optional[AMQPError] = None, wait: bool = False) -> None:
        try:
            if self.state not in [SessionState.UNMAPPED, SessionState.DISCARDING]:
                self._outgoing_end(error=error)
            for _, link in self.links.items():
                link.detach()
            new_state = SessionState.DISCARDING if error else SessionState.END_SENT
            self._set_state(new_state)
            self._wait_for_response(wait, SessionState.UNMAPPED)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.info("An error occurred when ending the session: %r", exc, extra=self.network_trace_params)
            self._set_state(SessionState.UNMAPPED)

    def create_receiver_link(self, source_address, **kwargs):
        assigned_handle = self._get_next_output_handle()
        link = ReceiverLink(
            self,
            handle=assigned_handle,
            source_address=source_address,
            network_trace=kwargs.pop("network_trace", self.network_trace),
            network_trace_params=dict(self.network_trace_params),
            **kwargs,
        )
        self.links[link.name] = link
        self._output_handles[assigned_handle] = link
        return link

    def create_sender_link(self, target_address, **kwargs):
        assigned_handle = self._get_next_output_handle()
        link = SenderLink(
            self,
            handle=assigned_handle,
            target_address=target_address,
            network_trace=kwargs.pop("network_trace", self.network_trace),
            network_trace_params=dict(self.network_trace_params),
            **kwargs,
        )
        self._output_handles[assigned_handle] = link
        self.links[link.name] = link
        return link

    def create_request_response_link_pair(self, endpoint, **kwargs):
        return ManagementLink(
            self,
            endpoint,
            network_trace=kwargs.pop("network_trace", self.network_trace),
            network_trace_params=dict(self.network_trace_params),
            **kwargs,
        )

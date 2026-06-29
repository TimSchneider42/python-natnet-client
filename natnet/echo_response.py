from typing import NamedTuple

from .packet_buffer import PacketBuffer
from .packet_component import PacketComponent
from .version import Version


class EchoResponse(
    PacketComponent,
    NamedTuple(
        "EchoResponseFields",
        (
            ("request_timestamp", int),  # echoed client monotonic-ns send time
            ("server_timestamp", int),  # server hi-res clock (QPC ticks)
        ),
    ),
):
    """Parsed NAT_ECHORESPONSE payload.

    NOTE: the echo handshake lives in Motive's closed binary, not the public SDK.
    The layout below (two little-endian uint64s, request timestamp first) is the
    expected shape.
    """

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "EchoResponse":
        request_timestamp = buffer.read_uint64()
        server_timestamp = buffer.read_uint64()
        return cls(request_timestamp, server_timestamp)

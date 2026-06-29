from typing import NamedTuple, Optional

from .packet_buffer import PacketBuffer
from .packet_component import PacketComponent
from .version import Version


class ServerInfo(
    PacketComponent,
    NamedTuple(
        "ServerInfoFields",
        (
            ("application_name", str),
            ("server_version", Version),
            ("nat_net_protocol_version", Version),
            # NatNet 3.0+ only (None otherwise).
            ("high_res_clock_frequency", Optional[int]),
            ("data_port", Optional[int]),
            ("is_multicast", Optional[bool]),
            ("multicast_group_address", Optional[str]),
        ),
    ),
):
    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "ServerInfo":
        application_name = buffer.read_string(256, static_length=True)
        server_version = Version(*buffer.read("BBBB"))
        nat_net_protocol_version = Version(*buffer.read("BBBB"))

        if nat_net_protocol_version >= Version(3):
            high_res_clock_frequency = buffer.read_uint64()
            data_port = buffer.read_uint16()
            is_multicast = buffer.read("B")[0] != 0
            multicast_group_address = ".".join(str(b) for b in buffer.read("BBBB"))
        else:
            high_res_clock_frequency = None
            data_port = None
            is_multicast = None
            multicast_group_address = None

        return cls(
            application_name,
            server_version,
            nat_net_protocol_version,
            high_res_clock_frequency,
            data_port,
            is_multicast,
            multicast_group_address,
        )

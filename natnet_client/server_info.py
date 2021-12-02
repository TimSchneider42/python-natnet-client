from typing import NamedTuple

from .packet_buffer import PacketBuffer
from .packet_component import PacketComponent
from .version import Version


class ServerInfo(PacketComponent, NamedTuple("ServerInfoFields", (
        ("application_name", str),
        ("server_version", Version),
        ("nat_net_protocol_version", Version)))):

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "ServerInfo":
        application_name = buffer.read_string(256, static_length=True)
        server_version = Version(*buffer.read("BBBB"))
        nat_net_protocol_version = Version(*buffer.read("BBBB"))
        return cls(application_name, server_version, nat_net_protocol_version)

from abc import ABC, abstractmethod

from .packet_buffer import PacketBuffer
from .version import Version


class PacketComponent(ABC):
    @classmethod
    @abstractmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "PacketComponent":
        pass

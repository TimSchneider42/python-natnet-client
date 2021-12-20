from abc import ABC, abstractmethod

from typing import Tuple

from .packet_buffer import PacketBuffer
from .version import Version


class PacketComponent(ABC):
    @classmethod
    @abstractmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "PacketComponent":
        pass


class PacketComponentArray(ABC):
    @classmethod
    @abstractmethod
    def read_array_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "Tuple[PacketComponent]":
        pass

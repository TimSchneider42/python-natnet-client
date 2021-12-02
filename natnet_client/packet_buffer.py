import struct
from typing import Optional, Union, Tuple, Any


class PacketBuffer:
    def __init__(self, data: bytes):
        self.__data = memoryview(data)  # Using a memoryview here ensures that slices do not create copies
        self.pointer = 0

    @property
    def data(self):
        return self.__data

    def read_string(self, max_length: Optional[int] = None, static_length: bool = False) -> str:
        if max_length is None:
            data_slice = self.__data[self.pointer:]
        else:
            data_slice = self.__data[self.pointer:self.pointer + max_length]
        str_enc, separator, remainder = bytes(data_slice).partition(b"\0")
        str_dec = str_enc.decode("utf-8")
        if static_length:
            assert max_length is not None
            self.pointer += max_length
        else:
            self.pointer += len(str_enc) + 1
        return str_dec

    def read(self, data_type: Union[struct.Struct, str]) -> Tuple[Any, ...]:
        if isinstance(data_type, str):
            data_type = struct.Struct(data_type)
        values = data_type.unpack_from(self.__data, offset=self.pointer)
        self.pointer += data_type.size
        return values

    def read_uint16(self) -> int:
        return self.read("H")[0]

    def read_uint32(self) -> int:
        return self.read("I")[0]

    def read_uint64(self) -> int:
        return self.read("L")[0]

    def read_float32(self) -> float:
        return self.read("f")[0]

    def read_float32_array(self, count: int) -> Tuple[float, ...]:
        return self.read("f" * count)

    def read_float64(self) -> float:
        return self.read("d")[0]

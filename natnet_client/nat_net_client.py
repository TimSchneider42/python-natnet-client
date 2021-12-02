import socket
from threading import Thread
import time
from typing import Optional

from .data_frame import DataFrame
from .event import Event
from .server_info import ServerInfo
from .data_descriptions import DataDescriptions
from .packet_buffer import PacketBuffer
from .version import Version


class NatNetClient:
    # Client/server message ids
    NAT_CONNECT = 0
    NAT_SERVERINFO = 1
    NAT_REQUEST = 2
    NAT_RESPONSE = 3
    NAT_REQUEST_MODELDEF = 4
    NAT_MODELDEF = 5
    NAT_REQUEST_FRAMEOFDATA = 6
    NAT_FRAMEOFDATA = 7
    NAT_MESSAGESTRING = 8
    NAT_DISCONNECT = 9
    NAT_KEEPALIVE = 10
    NAT_UNRECOGNIZED_REQUEST = 100

    def __init__(self, server_ip_address: str = "127.0.0.1", local_ip_address: str = "127.0.0.1",
                 multicast_address: str = "239.255.42.99", command_port: int = 1510, data_port: int = 1511,
                 use_multicast: bool = True):
        self.__server_ip_address = server_ip_address
        self.__local_ip_address = local_ip_address
        self.__multicast_address = multicast_address
        self.__command_port = command_port
        self.__data_port = data_port
        self.__use_multicast = use_multicast

        self.__server_info = None

        # NatNet stream version. This will be updated to the actual version the server is using during runtime.
        self.__current_protocol_version: Optional[Version] = None

        self.__command_thread = None
        self.__data_thread = None
        self.__command_socket = None
        self.__data_socket = None

        self.__stop_threads = False

        self.__on_data_frame_received_event = Event()
        self.__on_data_description_received_event = Event()

    @property
    def connected(self):
        return self.__command_socket is not None and self.__data_socket is not None and self.__server_info is not None

    # Create a command socket to attach to the NatNet stream
    def __create_command_socket(self):
        if self.__use_multicast:
            # Multicast case
            result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
            # allow multiple clients on same machine to use multicast group address/port
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                result.bind(("", 0))
            except socket.error as ex:
                print("Command socket error occurred:\n{}\nCheck Motive/Server mode requested mode agreement. "
                      "You requested Multicast".format(ex))
            # set to broadcast mode
            result.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        else:
            # Unicast case
            result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            try:
                result.bind((self.__local_ip_address, 0))
            except socket.error as ex:
                print("Command socket error occurred:\n{}\nCheck Motive/Server mode requested mode agreement. "
                      "You requested Multicast".format(ex))
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Ensure that thread can terminate
        result.settimeout(1.0)
        return result

    # Create a data socket to attach to the NatNet stream
    def __create_data_socket(self, port):
        if self.__use_multicast:
            # Multicast case
            result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)  # UDP
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                              socket.inet_aton(self.__multicast_address) + socket.inet_aton(self.__local_ip_address))
            try:
                result.bind((self.__local_ip_address, port))
            except socket.error as ex:
                print("Command socket error occurred:\n{}\nCheck Motive/Server mode requested mode agreement. "
                      "You requested Multicast".format(ex))
        else:
            # Unicast case
            result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                result.bind(("", 0))
            except socket.error as ex:
                print("Command socket error occurred:\n{}\nCheck Motive/Server mode requested mode agreement. "
                      "You requested Multicast".format(ex))

            if self.__multicast_address != "255.255.255.255":
                result.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                  socket.inet_aton(self.__multicast_address) + socket.inet_aton(
                                      self.__local_ip_address))
        # Ensure that thread can terminate
        result.settimeout(1.0)
        return result

    def __socket_thread_func(self, in_socket: socket.socket, use_multicast: bool = False,
                             recv_buffer_size: int = 64 * 1024, send_keep_alive: bool = False):
        data = bytearray(0)
        while not self.__stop_threads:
            # Block for input
            try:
                data, addr = in_socket.recvfrom(recv_buffer_size)
            except socket.timeout:
                pass
            except socket.error:
                if not self.__stop_threads:
                    raise
            if len(data) > 0:
                self.__process_message(PacketBuffer(data))
                data = bytearray(0)

            if not use_multicast and send_keep_alive:
                if not self.__stop_threads:
                    self.send_request(self.NAT_KEEPALIVE)
        return 0

    def __process_message(self, buffer: PacketBuffer):
        message_id = buffer.read_uint16()
        packet_size = buffer.read_uint16()
        if len(buffer.data) - 4 != packet_size:
            print("Warning: actual packet size ({}) not consistent with packet size in the header ({})".format(
                len(buffer.data) - 4, packet_size))
        if message_id == self.NAT_FRAMEOFDATA:
            data_frame = DataFrame.read_from_buffer(buffer, self.__current_protocol_version)
            self.__on_data_frame_received_event.call(data_frame)

        elif message_id == self.NAT_MODELDEF:
            data_descs = DataDescriptions.read_from_buffer(buffer, self.__current_protocol_version)
            self.__on_data_description_received_event.call(data_descs)

        elif message_id == self.NAT_SERVERINFO:
            self.__server_info = ServerInfo.read_from_buffer(buffer, self.__current_protocol_version)
            self.__current_protocol_version = self.__server_info.nat_net_protocol_version
        return message_id

    def send_request(self, command: int, command_str: str = ""):
        if command in [self.NAT_REQUEST_MODELDEF, self.NAT_REQUEST_FRAMEOFDATA, self.NAT_KEEPALIVE]:
            command_str = ""
        if command == self.NAT_CONNECT:
            command_str = "Ping"
        packet_size = len(command_str) + 1

        data = command.to_bytes(2, byteorder="little")
        data += packet_size.to_bytes(2, byteorder="little")

        data += command_str.encode("utf-8")
        data += b"\0"

        return self.__command_socket.sendto(data, (self.__server_ip_address, self.__command_port))

    def request_modeldef(self):
        self.send_request(self.NAT_REQUEST_MODELDEF)

    def send_command(self, command_str: str):
        assert self.connected
        return self.send_request(self.NAT_REQUEST, command_str)

    def connect(self, timeout: float = 5.0):
        assert self.__data_socket is None and self.__command_socket is None
        self.__data_socket = self.__create_data_socket(self.__data_port)
        self.__command_socket = self.__create_command_socket()

        self.__stop_threads = False
        # Create a separate thread for receiving data packets
        self.__data_thread = Thread(target=self.__socket_thread_func, args=(self.__data_socket, False))
        self.__data_thread.start()

        # Create a separate thread for receiving command packets
        self.__command_thread = Thread(target=self.__socket_thread_func,
                                       args=(self.__command_socket, self.__use_multicast),
                                       kwargs={"send_keep_alive": True})
        self.__command_thread.start()

        # Get NatNet and server versions
        self.send_request(self.NAT_CONNECT)

        start_time = time.time()
        while self.__server_info is None:
            # Waiting for reply from server
            if (time.time() - start_time) >= timeout:
                self.shutdown()
                raise TimeoutError()
            time.sleep(0.1)

    def shutdown(self):
        assert self.connected
        self.__stop_threads = True
        self.__command_socket.close()
        self.__data_socket.close()
        self.__command_thread.join()
        self.__data_thread.join()
        self.__command_socket = self.__command_thread = self.__data_socket = self.__data_thread = self.__server_info \
            = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    @property
    def on_data_frame_received_event(self) -> Event:
        return self.__on_data_frame_received_event

    @property
    def on_data_description_received_event(self) -> Event:
        return self.__on_data_description_received_event

    @property
    def server_info(self) -> Optional[ServerInfo]:
        return self.__server_info

    @property
    def can_change_protocol_version(self) -> bool:
        if self.__server_info is not None:
            return self.__server_info.nat_net_protocol_version >= Version(4) and not self.__use_multicast
        return False

    @property
    def protocol_version(self) -> Optional[Version]:
        return self.__current_protocol_version

    @protocol_version.setter
    def protocol_version(self, desired_version: Version):
        if not self.can_change_protocol_version:
            raise ValueError("Server does not support changing the NatNet protocol version.")
        desired_version = desired_version.truncate(2)
        if self.can_change_protocol_version and desired_version != self.__current_protocol_version.truncate(2):
            sz_command = "Bitstream,{}".format(desired_version)
            return_code = self.send_command(sz_command)
            if return_code >= 0:
                self.__current_protocol_version = desired_version
                self.send_command("TimelinePlay")
                time.sleep(0.1)
                for cmd in ["TimelinePlay", "TimelineStop", "SetPlaybackCurrentFrame,0", "TimelineStop"]:
                    self.send_command(cmd)
                time.sleep(2)
            else:
                raise ValueError("Failed to set NatNet protocol version")

    @property
    def server_ip_address(self) -> str:
        return self.__server_ip_address

    @property
    def local_ip_address(self) -> str:
        return self.__local_ip_address

    @property
    def multicast_address(self) -> str:
        return self.__multicast_address

    @property
    def command_port(self) -> int:
        return self.__command_port

    @property
    def data_port(self) -> int:
        return self.__data_port

    @property
    def use_multicast(self) -> bool:
        return self.__use_multicast

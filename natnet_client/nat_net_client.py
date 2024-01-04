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


class NatNetError(Exception):
    pass


class NatNetNetworkError(NatNetError):
    def __init__(self, socket_name: str, multicast: bool, inner_error: socket.error):
        super().__init__(
            f"{socket_name} socket error occurred:\n{inner_error}\nCheck Motive/Server mode requested mode agreement "
            f"(you requested {'multi' if multicast else 'uni'}cast).")
        self.inner_error = inner_error


class NatNetProtocolError(NatNetError):
    pass


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
        self.__command_socket: Optional[socket.socket] = None
        self.__data_socket: Optional[socket.socket] = None

        self.__stop_threads = False

        self.__on_data_frame_received_event = Event()
        self.__on_data_description_received_event = Event()

    @property
    def connected(self):
        return self.__command_socket is not None and self.__data_socket is not None and self.__server_info is not None

    @staticmethod
    def __create_socket(addr: str = "", port: int = 0):
        # Create a command socket to attach to the NatNet stream
        result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # allow multiple clients on same machine to use multicast group address/port
        result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            result.bind((addr, port))
        except:
            result.close()
            raise
        result.settimeout(0.0)
        return result

    def __create_command_socket(self):
        if self.__use_multicast:
            addr = ""
        else:
            addr = self.__local_ip_address
        try:
            result = self.__create_socket(addr, 0)
        except socket.error as ex:
            raise NatNetNetworkError("Command", self.__use_multicast, ex)

        if self.__use_multicast:
            # set to broadcast mode
            result.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return result

    # Create a data socket to attach to the NatNet stream
    def __create_data_socket(self, port):
        if self.__use_multicast:
            addr = self.__multicast_address
        else:
            addr = ""
            port = 0
        try:
            result = self.__create_socket(addr, port)
        except socket.error as ex:
            raise NatNetNetworkError("Data", self.__use_multicast, ex)

        if self.__use_multicast:
            result.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                              socket.inet_aton(self.__multicast_address) + socket.inet_aton(self.__local_ip_address))
        return result

    def __socket_thread_func(self, in_socket: socket.socket, recv_buffer_size: int = 64 * 1024,
                             send_keep_alive: bool = False):
        while not self.__stop_threads:
            # Use timeout to ensure that thread can terminate
            self.__process_socket(in_socket, recv_buffer_size=recv_buffer_size, send_keep_alive=send_keep_alive)

    def __process_socket(self, in_socket: socket.socket, recv_buffer_size: int = 64 * 1024,
                         send_keep_alive: bool = False):
        if send_keep_alive:
            self.send_request(self.NAT_KEEPALIVE)
        try:
            data, addr = in_socket.recvfrom(recv_buffer_size)
            if len(data) > 0:
                self.__process_message(PacketBuffer(data))
                return True
        except (BlockingIOError, socket.timeout):
            pass
        return False

    def __process_message(self, buffer: PacketBuffer):
        message_id = buffer.read_uint16()
        packet_size = buffer.read_uint16()
        if len(buffer.data) - 4 != packet_size:
            print(f"Warning: actual packet size ({len(buffer.data) - 4}) not consistent with packet size in the "
                  f"header ({packet_size})")
        if message_id == self.NAT_SERVERINFO:
            self.__server_info = ServerInfo.read_from_buffer(buffer, self.__current_protocol_version)
            self.__current_protocol_version = self.__server_info.nat_net_protocol_version
        else:
            if self.__current_protocol_version is None:
                print(f"Warning: dropping packet of type {message_id} as server info has not been received yet.")
            if message_id == self.NAT_FRAMEOFDATA:
                data_frame = DataFrame.read_from_buffer(buffer, self.__current_protocol_version)
                self.__on_data_frame_received_event.call(data_frame)
            elif message_id == self.NAT_MODELDEF:
                data_descs = DataDescriptions.read_from_buffer(buffer, self.__current_protocol_version)
                self.__on_data_description_received_event.call(data_descs)
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
        if not self.connected:
            raise NatNetError("NatNet client is not connected to a server.")
        return self.send_request(self.NAT_REQUEST, command_str)

    def connect(self, timeout: float = 5.0):
        if not self.connected:
            self.__data_socket = self.__create_data_socket(self.__data_port)
            self.__command_socket = self.__create_command_socket()

            # Get NatNet and server versions
            self.send_request(self.NAT_CONNECT)

            start_time = time.time()
            while self.__server_info is None:
                # Waiting for reply from server
                self.__process_socket(self.__command_socket, send_keep_alive=not self.__use_multicast)
                if self.__server_info is None and (time.time() - start_time) >= timeout:
                    self.shutdown()
                    raise TimeoutError()
                time.sleep(0.1)

    def run_async(self):
        if not self.running_asynchronously:
            self.__stop_threads = False

            # To ensure that threads can terminate
            self.__data_socket.settimeout(0.1)
            self.__command_socket.settimeout(0.1)

            # Create a separate thread for receiving data packets
            self.__data_thread = Thread(target=self.__socket_thread_func, args=(self.__data_socket,))
            self.__data_thread.start()

            # Create a separate thread for receiving command packets
            self.__command_thread = Thread(
                target=self.__socket_thread_func, args=(self.__command_socket,),
                kwargs={"send_keep_alive": not self.__use_multicast})
            self.__command_thread.start()

    def stop_async(self):
        if self.running_asynchronously:
            self.__stop_threads = True
            if self.__command_thread is not None:
                self.__command_thread.join()
            if self.__data_thread is not None:
                self.__data_thread.join()
            self.__command_thread = self.__data_thread = None
            self.__data_socket.settimeout(0.0)
            self.__command_socket.settimeout(0.0)

    def update_sync(self):
        assert not self.running_asynchronously, "Cannot update synchronously while running asynchronously."
        while self.__process_socket(self.__data_socket):
            pass
        while self.__process_socket(self.__command_socket, send_keep_alive=not self.__use_multicast):
            pass

    def shutdown(self):
        self.stop_async()
        if self.__command_socket is not None:
            self.__command_socket.close()
        if self.__data_socket is not None:
            self.__data_socket.close()
        self.__command_socket = self.__data_socket = self.__server_info = None

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
            raise NatNetProtocolError("Server does not support changing the NatNet protocol version.")
        desired_version = desired_version.truncate(2)
        if self.can_change_protocol_version and desired_version != self.__current_protocol_version.truncate(2):
            sz_command = f"Bitstream,{desired_version}"
            return_code = self.send_command(sz_command)
            if return_code >= 0:
                self.__current_protocol_version = desired_version
                self.send_command("TimelinePlay")
                time.sleep(0.1)
                for cmd in ["TimelinePlay", "TimelineStop", "SetPlaybackCurrentFrame,0", "TimelineStop"]:
                    self.send_command(cmd)
                time.sleep(2)
            else:
                raise NatNetProtocolError("Failed to set NatNet protocol version")

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

    @property
    def running_asynchronously(self):
        return self.__command_thread is not None or self.__data_thread is not None

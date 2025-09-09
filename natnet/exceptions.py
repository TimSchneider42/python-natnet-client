import socket


class NatNetError(Exception):
    pass


class NatNetNetworkError(NatNetError):
    def __init__(self, socket_name: str, multicast: bool, inner_error: socket.error):
        super().__init__(
            f"{socket_name} socket error occurred:\n{inner_error}\nCheck Motive/Server mode requested mode agreement "
            f"(you requested {'multi' if multicast else 'uni'}cast)."
        )
        self.inner_error = inner_error


class NatNetProtocolError(NatNetError):
    pass

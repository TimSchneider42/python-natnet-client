import time
from collections import deque
from threading import Lock
from typing import Deque, Optional, Tuple


class ClockSync:
    """Estimates the offset between the server's hi-res clock and the local
    monotonic clock via Cristian's algorithm with a min-RTT filter.

    Offset relates the clocks as ``server_seconds ~= client_seconds + offset``.
    Thread-safe: samples are added from the command thread and read elsewhere.
    """

    def __init__(self, frequency: int, window: int = 10):
        self.__frequency = frequency
        self.__lock = Lock()
        self.__samples: Deque[Tuple[float, float]] = deque(maxlen=window)

    @staticmethod
    def estimate_offset(
        t_send_ns: int, t_recv_ns: int, server_ticks: int, frequency: int
    ) -> Tuple[float, float]:
        """Cristian's algorithm for one round trip. Returns (rtt, offset) in
        seconds; the server instant is assumed to occur at the round-trip
        midpoint in client time."""
        t_send = t_send_ns / 1e9
        t_recv = t_recv_ns / 1e9
        rtt = t_recv - t_send
        offset = server_ticks / frequency - (t_send + rtt / 2.0)
        return rtt, offset

    def add_sample(self, t_send_ns: int, t_recv_ns: int, server_ticks: int) -> None:
        sample = self.estimate_offset(
            t_send_ns, t_recv_ns, server_ticks, self.__frequency
        )
        with self.__lock:
            self.__samples.append(sample)

    def __best(self) -> Optional[Tuple[float, float]]:
        # Lowest-RTT sample in the window; caller holds the lock.
        if not self.__samples:
            return None
        return min(self.__samples, key=lambda s: s[0])

    @property
    def synchronized(self) -> bool:
        with self.__lock:
            return len(self.__samples) > 0

    @property
    def offset(self) -> Optional[float]:
        with self.__lock:
            best = self.__best()
        return best[1] if best is not None else None

    @property
    def rtt(self) -> Optional[float]:
        with self.__lock:
            best = self.__best()
        return best[0] if best is not None else None

    def seconds_since_host_timestamp(self, host_timestamp: int) -> Optional[float]:
        with self.__lock:
            best = self.__best()
        if best is None:
            return None
        host_client_time = host_timestamp / self.__frequency - best[1]
        return time.monotonic() - host_client_time

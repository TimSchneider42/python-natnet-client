from dataclasses import dataclass, fields
from inspect import isclass
from typing import Tuple, Optional

from .data_types import Vec3, Vec4
from .packet_buffer import PacketBuffer
from .packet_component import PacketComponent
from .version import Version


@dataclass(frozen=True)
class FramePrefix(PacketComponent):
    frame_number: int

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "FramePrefix":
        return FramePrefix(buffer.read_uint32())


@dataclass(frozen=True)
class MarkerSet(PacketComponent):
    model_name: str
    marker_pos_list: Tuple[Vec3, ...]

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "MarkerSet":
        model_name = buffer.read_string()
        marker_count = buffer.read_uint32()
        marker_pos_list = [buffer.read_float32_array(3) for _ in range(marker_count)]
        return MarkerSet(model_name, tuple(marker_pos_list))


# Only used up until version 3.0, where this information has been moved to the description
@dataclass(frozen=True)
class RigidBodyMarker:
    pos: Vec3
    id_num: Optional[int]
    size: Optional[int]


@dataclass(frozen=True)
class RigidBody(PacketComponent):
    id_num: int
    pos: Vec3
    rot: Vec4
    markers: Optional[Tuple[RigidBodyMarker, ...]]
    tracking_valid: Optional[bool]
    marker_error: Optional[float]

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "RigidBody":
        id_num = buffer.read_uint32()
        pos = buffer.read_float32_array(3)
        rot = buffer.read_float32_array(4)
        # RB Marker Data ( Before version 3.0.  After Version 3.0 Marker data is in description )
        if protocol_version < Version(3, 0):
            marker_count = buffer.read_uint32()
            marker_positions = [buffer.read_float32_array(3) for _ in range(marker_count)]

            if protocol_version >= Version(2):
                marker_ids = [buffer.read_uint32() for _ in range(marker_count)]
                marker_sizes = [buffer.read_float32() for _ in range(marker_count)]
            else:
                marker_ids = marker_sizes = [None for _ in range(marker_count)]

            markers = [RigidBodyMarker(*f) for f in zip(marker_positions, marker_ids, marker_sizes)]
        else:
            markers = None
        if protocol_version >= Version(2):
            marker_error = buffer.read_float32()
        else:
            marker_error = None

        # Version 2.6 and later
        if protocol_version >= Version(2, 6):
            param = buffer.read_uint16()
            tracking_valid = (param & 0x01) != 0
        else:
            tracking_valid = None

        return RigidBody(id_num, pos, rot, markers, tracking_valid, marker_error)


@dataclass(frozen=True)
class Skeleton(PacketComponent):
    id_num: int
    rigid_bodies: Tuple[RigidBody, ...]

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "Skeleton":
        id_num = buffer.read_uint32()
        rigid_body_count = buffer.read_uint32()
        rigid_bodies = [RigidBody.read_from_buffer(buffer, protocol_version) for _ in range(rigid_body_count)]

        return Skeleton(id_num, tuple(rigid_bodies))


@dataclass(frozen=True)
class LabeledMarker(PacketComponent):
    id_num: int
    pos: Vec3
    size: int
    param: Optional[int]
    residual: Optional[float]

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "LabeledMarker":
        id_num = buffer.read_uint32()
        pos = buffer.read_float32_array(3)
        size = buffer.read_float32()

        # Version 2.6 and later
        if protocol_version >= Version(2, 6):
            param = buffer.read_uint16()
        else:
            param = None

        # Version 3.0 and later
        if protocol_version >= Version(3):
            residual = buffer.read_float32()
        else:
            residual = None

        return cls(id_num, pos, size, param, residual)

    @property
    def model_id(self):
        return self.id_num >> 16

    @property
    def marker_id(self):
        return self.id_num & 0x0000ffff

    @property
    def occluded(self):
        return bool(self.param & 0x01)

    @property
    def point_cloud_solved(self):
        return bool(self.param & 0x02)

    @property
    def model_solved(self):
        return bool(self.param & 0x04)

    @property
    def has_model(self):
        return bool(self.param & 0x08)

    @property
    def unlabeled(self):
        return bool(self.param & 0x10)

    @property
    def active(self):
        return bool(self.param & 0x20)


@dataclass(frozen=True)
class ForcePlate(PacketComponent):
    id_num: int
    channel_arrays: Tuple[Tuple[float, ...], ...]

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "ForcePlate":
        id_num = buffer.read_uint32()
        channel_count = buffer.read_uint32()
        channel_arrays = tuple(buffer.read_float32_array(buffer.read_uint32()) for _ in range(channel_count))
        return ForcePlate(id_num, channel_arrays)


@dataclass(frozen=True)
class Device(PacketComponent):
    id_num: int
    channel_arrays: Tuple[Tuple[float, ...], ...]

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "Device":
        id_num = buffer.read_uint32()
        channel_count = buffer.read_uint32()
        channel_arrays = tuple(buffer.read_float32_array(buffer.read_uint32()) for _ in range(channel_count))
        return Device(id_num, channel_arrays)


@dataclass(frozen=True)
class FrameSuffix(PacketComponent):
    timecode: int
    timecode_sub: int
    timestamp: float
    stamp_camera_mid_exposure: Optional[int]
    stamp_data_received: Optional[int]
    stamp_transmit: Optional[int]
    param: int
    is_recording: bool
    tracked_models_changed: bool

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "FrameSuffix":
        # Timecode
        timecode = buffer.read_uint32()
        timecode_sub = buffer.read_uint32()

        # Timestamp (increased to double precision in 2.7 and later)
        if protocol_version >= Version(2, 7):
            timestamp = buffer.read_float64()
        else:
            timestamp = buffer.read_float32()

        # Hires Timestamp (Version 3.0 and later)
        if protocol_version >= Version(3):
            stamp_camera_mid_exposure = buffer.read_uint64()
            stamp_data_received = buffer.read_uint64()
            stamp_transmit = buffer.read_uint64()
        else:
            stamp_camera_mid_exposure = stamp_data_received = stamp_transmit = None

        # Frame parameters
        param = buffer.read_uint16()
        is_recording = (param & 0x01) != 0
        tracked_models_changed = (param & 0x02) != 0

        return FrameSuffix(timecode, timecode_sub, timestamp, stamp_camera_mid_exposure, stamp_data_received,
                           stamp_transmit, param, is_recording, tracked_models_changed)


@dataclass(frozen=True)
class DataFrame(PacketComponent):
    prefix: FramePrefix
    marker_sets: Tuple[MarkerSet, ...]
    unlabeled_marker_pos: Tuple[Vec3, ...]
    rigid_bodies: Tuple[RigidBody, ...]
    skeletons: Tuple[Skeleton, ...]
    labeled_markers: Tuple[LabeledMarker, ...]
    force_plates: Tuple[ForcePlate, ...]
    devices: Tuple[Device, ...]
    suffix: FrameSuffix

    MIN_VERSIONS = {
        "prefix": Version(0),
        "marker_sets": Version(0),
        "unlabeled_marker_pos": Version(0),
        "rigid_bodies": Version(0),
        "skeletons": Version(2, 1),
        "labeled_markers": Version(2, 3),
        "force_plates": Version(2, 9),
        "devices": Version(2, 11),
        "suffix": Version(0)
    }

    @classmethod
    def read_from_buffer(cls, buffer: PacketBuffer, protocol_version: Version) -> "DataFrame":
        kwargs = {}

        for field in fields(cls):
            if protocol_version >= cls.MIN_VERSIONS[field.name]:
                if isclass(field.type) and issubclass(field.type, PacketComponent):
                    kwargs[field.name] = field.type.read_from_buffer(buffer, protocol_version)
                else:
                    # Type is a tuple
                    element_count = buffer.read_uint32()
                    generic_type = field.type.__args__[0]
                    if generic_type == Vec3:
                        kwargs[field.name] = tuple(buffer.read_float32_array(3) for _ in range(element_count))
                    else:
                        kwargs[field.name] = tuple(
                            generic_type.read_from_buffer(buffer, protocol_version) for _ in range(element_count))
            else:
                kwargs[field.name] = None

        return cls(**kwargs)

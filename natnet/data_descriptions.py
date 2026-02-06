from typing import NamedTuple, Tuple, Optional

from .data_types import Vec3, Vec4
from .exceptions import NatNetProtocolError
from .packet_buffer import PacketBuffer
from .packet_component import PacketComponent, PacketComponentArray
from .version import Version


class MarkerSetDescription(
    PacketComponent,
    NamedTuple(
        "MarkerSetDescriptionFields", (("name", str), ("marker_names", Tuple[str, ...]))
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "MarkerSetDescription":
        name = buffer.read_string()

        marker_count = buffer.read_uint32()
        marker_names = [buffer.read_string() for _ in range(marker_count)]
        return MarkerSetDescription(name, tuple(marker_names))


class RigidBodyMarkerDescription(
    PacketComponentArray,
    NamedTuple(
        "RigidBodyMarkerDescriptionFields",
        (("name", Optional[str]), ("active_label", int), ("pos", Vec3)),
    ),
):

    @classmethod
    def read_array_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "Tuple[RigidBodyMarkerDescription, ...]":
        marker_count = buffer.read_uint32()
        pos = [buffer.read_float32_array(3) for _ in range(marker_count)]
        active_labels = [buffer.read_uint32() for _ in range(marker_count)]
        names = (
            [buffer.read_string() for _ in range(marker_count)]
            if protocol_version >= Version(4)
            else [None] * marker_count
        )
        return tuple(
            RigidBodyMarkerDescription(*a) for a in zip(names, active_labels, pos)
        )


class RigidBodyDescription(
    PacketComponent,
    NamedTuple(
        "RigidBodyDescriptionFields",
        (
            ("name", Optional[str]),
            ("id_num", int),
            ("parent_id", int),
            ("pos", Vec3),
            ("quat", Optional[Vec4]),
            ("markers", Tuple[RigidBodyMarkerDescription, ...]),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "RigidBodyDescription":
        # Version 2.0 or higher
        name = buffer.read_string() if protocol_version >= Version(2) else None

        new_id = buffer.read_uint32()
        parent_id = buffer.read_uint32()
        pos = buffer.read_float32_array(3)

        # Version 4.2 and higher, rigid body has quaternion
        quat = (
            buffer.read_float32_array(4) if protocol_version >= Version(4, 2) else None
        )

        # Version 3.0 and higher, rigid body marker information contained in description
        if protocol_version >= Version(3):
            marker_descriptions = RigidBodyMarkerDescription.read_array_from_buffer(
                buffer, protocol_version
            )
        else:
            marker_descriptions = []

        return RigidBodyDescription(
            name, new_id, parent_id, pos, quat, tuple(marker_descriptions)
        )


class SkeletonDescription(
    PacketComponent,
    NamedTuple(
        "SkeletonDescriptionFields",
        (
            ("name", str),
            ("id_num", int),
            ("rigid_body_descriptions", Tuple[RigidBodyDescription, ...]),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "SkeletonDescription":
        name = buffer.read_string()
        new_id = buffer.read_uint32()
        rigid_body_count = buffer.read_uint32()

        # Loop over all Rigid Bodies
        rigid_body_descs = [
            RigidBodyDescription.read_from_buffer(buffer, protocol_version)
            for _ in range(rigid_body_count)
        ]
        return SkeletonDescription(name, new_id, tuple(rigid_body_descs))


class ForcePlateDescription(
    PacketComponent,
    NamedTuple(
        "ForcePlateDescriptionFields",
        (
            ("id_num", int),
            ("serial_number", str),
            ("width", float),
            ("length", float),
            ("position", Vec3),
            ("cal_matrix", Tuple[Tuple[float, ...]]),
            ("corners", Tuple[Vec3, Vec3, Vec3, Vec3]),
            ("plate_type", int),
            ("channel_data_type", int),
            ("channel_list", Tuple[str, ...]),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> Optional["ForcePlateDescription"]:
        if protocol_version >= Version(3):
            new_id = buffer.read_uint32()
            serial_number = buffer.read_string()
            width = buffer.read_float32()
            length = buffer.read_float32()
            origin = buffer.read_float32_array(3)

            cal_matrix_flat = buffer.read_float32_array(12 * 12)
            cal_matrix = [cal_matrix_flat[i * 12 : (i + 1) * 12] for i in range(12)]

            corners_flat = buffer.read_float32_array(3 * 3)
            corners = [corners_flat[i * 3 : (i + 1) * 3] for i in range(3)]

            plate_type = buffer.read_uint32()
            channel_data_type = buffer.read_uint32()
            num_channels = buffer.read_uint32()

            channels = [buffer.read_string() for _ in range(num_channels)]

            return ForcePlateDescription(
                new_id,
                serial_number,
                width,
                length,
                origin,
                tuple(cal_matrix),
                tuple(corners),
                plate_type,
                channel_data_type,
                tuple(channels),
            )
        else:
            return None


class DeviceDescription(
    PacketComponent,
    NamedTuple(
        "DeviceDescriptionFields",
        (
            ("id_num", int),
            ("name", str),
            ("serial_number", str),
            ("device_type", int),
            ("channel_data_type", int),
            ("channel_names", Tuple[str, ...]),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> Optional["DeviceDescription"]:
        if protocol_version >= Version(3):
            new_id = buffer.read_uint32()
            name = buffer.read_string()
            serial_number = buffer.read_string()
            device_type = buffer.read_uint32()
            channel_data_type = buffer.read_uint32()
            num_channels = buffer.read_uint32()

            # Channel Names list of NoC strings
            channel_names = [buffer.read_string() for _ in range(num_channels)]

            return DeviceDescription(
                new_id,
                name,
                serial_number,
                device_type,
                channel_data_type,
                tuple(channel_names),
            )
        else:
            return None


class CameraDescription(
    PacketComponent,
    NamedTuple(
        "CameraDescriptionFields",
        (("name", str), ("position", Vec3), ("orientation_quat", Vec4)),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "CameraDescription":
        name = buffer.read_string()
        position = buffer.read_float32_array(3)
        orientation = buffer.read_float32_array(4)

        return CameraDescription(name, position, orientation)


class MarkerDescription(
    PacketComponent,
    NamedTuple(
        "MarkerDescriptionFields",
        (
            ("name", str),
            ("marker_id", int),
            ("position", Vec3),
            ("marker_size", float),
            ("marker_params", int),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "MarkerDescription":
        name = buffer.read_string()
        marker_id = buffer.read_uint32()
        position = buffer.read_float32_array(3)
        marker_size = buffer.read_float32()
        marker_params = buffer.read_uint16()

        return MarkerDescription(name, marker_id, position, marker_size, marker_params)


class AssetDescription(
    PacketComponent,
    NamedTuple(
        "AssetDescriptionFields",
        (
            ("name", str),
            ("asset_type", int),
            ("asset_id", int),
            ("rigid_body_descriptions", Tuple[RigidBodyDescription, ...]),
            ("marker_descriptions", Tuple[MarkerDescription, ...]),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "AssetDescription":
        name = buffer.read_string()
        asset_type = buffer.read_uint32()
        asset_id = buffer.read_uint32()

        num_rbs = buffer.read_uint32()
        rigid_body_descriptions = [
            RigidBodyDescription.read_from_buffer(buffer, protocol_version)
            for _ in range(num_rbs)
        ]

        num_markers = buffer.read_uint32()
        marker_descriptions = [
            MarkerDescription.read_from_buffer(buffer, protocol_version)
            for _ in range(num_markers)
        ]

        return AssetDescription(
            name,
            asset_type,
            asset_id,
            tuple(rigid_body_descriptions),
            tuple(marker_descriptions),
        )


class DataDescriptions(
    PacketComponent,
    NamedTuple(
        "DataDescriptions",
        (
            ("marker_sets", Tuple[MarkerSetDescription, ...]),
            ("rigid_bodies", Tuple[RigidBodyDescription, ...]),
            ("skeletons", Tuple[SkeletonDescription, ...]),
            ("force_plates", Tuple[ForcePlateDescription, ...]),
            ("devices", Tuple[DeviceDescription, ...]),
            ("cameras", Tuple[CameraDescription, ...]),
            ("assets", Tuple[AssetDescription, ...]),
        ),
    ),
):

    @classmethod
    def read_from_buffer(
        cls, buffer: PacketBuffer, protocol_version: Version
    ) -> "DataDescriptions":
        data_desc_types = {
            0: ("marker_sets", MarkerSetDescription),
            1: ("rigid_bodies", RigidBodyDescription),
            2: ("skeletons", SkeletonDescription),
            3: ("force_plates", ForcePlateDescription),
            4: ("devices", DeviceDescription),
            5: ("cameras", CameraDescription),
            6: ("assets", AssetDescription),
        }
        data_dict = {n: [] for i, (n, f) in data_desc_types.items()}
        # # of data sets to process
        dataset_count = buffer.read_uint32()
        for i in range(0, dataset_count):
            data_type = buffer.read_uint32()
            if protocol_version >= Version(4, 1):
                _dataset_size = buffer.read_uint32()
            if data_type in data_desc_types:
                name, desc_type = data_desc_types[data_type]
                unpacked_data = desc_type.read_from_buffer(buffer, protocol_version)
                data_dict[name].append(unpacked_data)
            else:
                raise NatNetProtocolError(
                    f"Unknown data type {data_type} encountered while parsing data descriptions. "
                    f"Stopped processing at {buffer.pointer}/{len(buffer.data)} bytes, "
                    f"({i + 1}/{dataset_count}) datasets."
                )
        return DataDescriptions(**data_dict)

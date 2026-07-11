"""将底盘 WS 激光栅格点（图像像素）转为 RViz PointCloud2。"""

from __future__ import annotations

import struct
from typing import Iterable

from agilex_chassis_bridge.map_conversion import pixel_pose_to_rviz


def pixel_points_to_pointcloud2(
    points: Iterable[tuple[float, float]],
    map_height: int,
    frame_id: str,
    stamp,
):
    from sensor_msgs.msg import PointCloud2, PointField

    packed: list[bytes] = []
    for px, py in points:
        x, y = pixel_pose_to_rviz(px, py, map_height)
        packed.append(struct.pack("<fff", x, y, 0.0))

    msg = PointCloud2()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.height = 1
    msg.width = len(packed)
    msg.fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = msg.point_step * msg.width
    msg.is_dense = True
    msg.data = b"".join(packed)
    return msg

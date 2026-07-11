"""将底盘 PNG 地图转换为 ROS OccupancyGrid 与 Image。"""

from __future__ import annotations

import math
from io import BytesIO

import numpy as np
from PIL import Image as PilImage

from agilex_client.coords import MapInfo


def png_bytes_to_occupancy_grid(
    png_bytes: bytes,
    info: MapInfo,
    frame_id: str,
    stamp,
) -> tuple[object, object]:
    from nav_msgs.msg import OccupancyGrid
    from sensor_msgs.msg import Image as RosImage
    from std_msgs.msg import Header

    image = PilImage.open(BytesIO(png_bytes)).convert("L")
    arr = np.array(image)

    # 松灵 PNG：浅色空闲、深色障碍。阈值化到 ROS occupancy [0,100], unknown=-1
    grid = np.full(arr.shape, -1, dtype=np.int8)
    grid[arr > 200] = 0
    grid[arr < 80] = 100

    occ = OccupancyGrid()
    occ.header = Header(stamp=stamp, frame_id=frame_id)
    occ.info.resolution = 1.0
    occ.info.width = info.width
    occ.info.height = info.height
    occ.info.origin.position.x = 0.0
    occ.info.origin.position.y = 0.0
    occ.info.origin.position.z = 0.0
    occ.info.origin.orientation.w = 1.0
    # RViz/nav_msgs 约定：原点在左下，行 0 为南侧；像素 API 仍为图像左上
    occ.data = np.flipud(grid).flatten().tolist()

    img_msg = RosImage()
    img_msg.header = occ.header
    img_msg.height, img_msg.width = arr.shape
    img_msg.encoding = "mono8"
    img_msg.step = img_msg.width
    img_msg.data = arr.astype(np.uint8).tobytes()

    return occ, img_msg


def theta_deg_to_quaternion(theta_deg: float):
    from geometry_msgs.msg import Quaternion

    yaw = math.radians(theta_deg)
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


def quaternion_to_theta_deg(quaternion) -> float:
    """从四元数提取 yaw（度）。"""
    x = quaternion.x
    y = quaternion.y
    z = quaternion.z
    w = quaternion.w
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return math.degrees(yaw) % 360.0


def rviz_pose_to_pixel(x_rviz: float, y_rviz: float, map_height: int) -> tuple[float, float]:
    """RViz/TF 地图坐标 → 图像像素坐标。"""
    return float(x_rviz), float(map_height) - float(y_rviz)


def pixel_pose_to_rviz(x_pixel: float, y_pixel: float, map_height: int) -> tuple[float, float]:
    """图像像素坐标 → RViz/TF 地图坐标。"""
    return float(x_pixel), float(map_height) - float(y_pixel)

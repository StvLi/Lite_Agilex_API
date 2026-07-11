"""地图坐标约定。

对外接口（ROS2 / Web / VLM 导出）统一使用 **图像像素坐标**：
- 原点：地图 PNG 左上角
- x：向右增大（0 … width-1）
- y：向下增大（0 … height-1）
- theta_deg：朝向角度（度），与底盘 WebSocket 一致

底盘 HTTP/WS 原生即使用上述像素坐标。`grid_to_world` / `world_to_grid` 仅保留给
需要公制米制换算的内部场景，不再是默认对外格式。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapInfo:
    name: str
    width: int
    height: int
    origin_x: float
    origin_y: float
    resolution: float

    @classmethod
    def from_api(cls, name: str, data: dict) -> "MapInfo":
        return cls(
            name=name,
            width=int(data["width"]),
            height=int(data["height"]),
            origin_x=float(data["originX"]),
            origin_y=float(data["originY"]),
            resolution=float(data["resolution"]),
        )


def grid_to_world(px: float, py: float, info: MapInfo) -> tuple[float, float]:
    """图像像素 → 公制世界坐标（米）。仅内部换算使用。"""
    world_x = px * info.resolution + info.origin_x
    world_y = (info.height - py) * info.resolution + info.origin_y
    return world_x, world_y


def world_to_grid(wx: float, wy: float, info: MapInfo) -> tuple[float, float]:
    """公制世界坐标（米）→ 图像像素。仅内部换算使用。"""
    px = (wx - info.origin_x) / info.resolution
    py = info.height - (wy - info.origin_y) / info.resolution
    return px, py

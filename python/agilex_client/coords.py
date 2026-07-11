"""栅格坐标（WS 位姿 / PNG 像素）与世界坐标（导航 API）互转。"""

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
    world_x = px * info.resolution + info.origin_x
    world_y = (info.height - py) * info.resolution + info.origin_y
    return world_x, world_y


def world_to_grid(wx: float, wy: float, info: MapInfo) -> tuple[float, float]:
    px = (wx - info.origin_x) / info.resolution
    py = info.height - (wy - info.origin_y) / info.resolution
    return px, py

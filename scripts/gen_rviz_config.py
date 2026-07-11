#!/usr/bin/env python3
"""根据地图尺寸生成 RViz 配置：全图俯视 + 仅保留 2D Pose Estimate 工具。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from agilex_client import AgilexClient, load_config  # noqa: E402

RVIZ_OUT = (
    ROOT / "ros2_ws" / "src" / "agilex_chassis_bridge" / "rviz" / "chassis_map.rviz"
)

WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900
MAP_MARGIN = 1.05
DEFAULT_ZOOM_FACTOR = 1.25


def _load_map_size(cfg: dict) -> tuple[int, int, str]:
    debug = cfg["debug_site"]
    map_name = debug["map_name"]
    width = int(debug.get("map_width", 0) or 0)
    height = int(debug.get("map_height", 0) or 0)
    if width > 0 and height > 0:
        return width, height, map_name

    chassis = cfg["chassis"]
    auth = cfg["auth"]
    if not auth.get("username") or not auth.get("password"):
        raise RuntimeError(
            "未配置 map_width/map_height，且缺少 auth 凭据，无法从底盘拉取地图尺寸"
        )
    client = AgilexClient(
        http_base=chassis["http_base"],
        ws_base=chassis["ws_base"],
        username=auth["username"],
        password=auth["password"],
        timeout=float(cfg["network"]["http_timeout_sec"]),
    )
    client.login()
    info = client.get_map_info(map_name)
    return info.width, info.height, map_name


def _compute_scale(map_width: int, map_height: int, zoom_factor: float) -> float:
    # TopDownOrtho::Scale 越大画面越“放大”；在容纳全图基础上乘以 zoom_factor 适当放大。
    scale_w = WINDOW_WIDTH / (map_width * MAP_MARGIN)
    scale_h = WINDOW_HEIGHT / (map_height * MAP_MARGIN)
    return round(min(scale_w, scale_h) * zoom_factor, 3)


def _render_rviz(
    map_width: int,
    map_height: int,
    map_name: str,
    scale: float,
) -> str:
    cx = map_width / 2.0
    cy = map_height / 2.0
    return f"""Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Tool Properties
    Name: Tool Properties
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Alpha: 0.9
      Class: rviz_default_plugins/Map
      Color Scheme: map
      Draw Behind: true
      Enabled: true
      Name: AgilexMap
      Topic:
        Depth: 1
        Durability Policy: Transient Local
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /agilex/map
      Value: true
    - Alpha: 0.85
      Class: rviz_default_plugins/PointCloud2
      Color: 255; 64; 64
      Color Transformer: FlatColor
      Decay Time: 0
      Enabled: true
      Name: LaserOnMap
      Size (Pixels): 3
      Style: Points
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /agilex/laser_map
      Use Fixed Frame: true
      Value: true
    - Alpha: 1
      Class: rviz_default_plugins/Pose
      Color: 255; 120; 0
      Enabled: true
      Head Length: 12
      Head Radius: 6
      Name: RobotPose
      Shaft Length: 28
      Shaft Radius: 3
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /agilex/pose_rviz
      Value: true
    - Alpha: 1
      Class: rviz_default_plugins/Pose
      Color: 0; 200; 80
      Enabled: true
      Head Length: 14
      Head Radius: 7
      Name: InitPosePreview
      Shaft Length: 32
      Shaft Radius: 3
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /agilex/init_pose_preview
      Value: true
    - Alpha: 1
      Class: rviz_default_plugins/Axes
      Enabled: true
      Length: 40
      Name: RobotAxes
      Radius: 2
      Reference Frame: base_link
      Value: true
    - Class: rviz_default_plugins/TF
      Enabled: true
      Frame Timeout: 15
      Marker Scale: 1.5
      Name: TF
      Show Arrows: true
      Show Axes: false
      Show Names: true
      Value: true
  Enabled: true
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: agilex_map
  Name: root
  Tools:
    - Class: rviz_default_plugins/SetInitialPose
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /initialpose
    - Class: rviz_default_plugins/MoveCamera
  Value: true
  Views:
    Current:
      Angle: 0
      Class: rviz_default_plugins/TopDownOrtho
      Enable Stereo Rendering:
        Stereo Eye Separation: 0.05999999865889549
        Stereo Focal Distance: 1
        Swap Stereo Eyes: false
        Value: false
      Invert Z Axis: false
      Name: Current View
      Near Clip Distance: 0.009999999776482582
      Scale: {scale}
      Target Frame: agilex_map
      Value: TopDownOrtho (rviz)
      X: {cx}
      Y: {cy}
    Saved: ~
Window Geometry:
  Height: {WINDOW_HEIGHT}
  Width: {WINDOW_WIDTH}
"""


def main() -> int:
    cfg = load_config()
    map_width, map_height, map_name = _load_map_size(cfg)
    zoom_factor = float(cfg["debug_site"].get("rviz_zoom_factor", DEFAULT_ZOOM_FACTOR))
    scale = _compute_scale(map_width, map_height, zoom_factor)
    RVIZ_OUT.write_text(
        _render_rviz(map_width, map_height, map_name, scale),
        encoding="utf-8",
    )
    print(
        f"已生成 RViz 配置: {map_name} {map_width}x{map_height}, "
        f"center=({map_width/2:.1f},{map_height/2:.1f}), "
        f"scale={scale}, zoom={zoom_factor}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

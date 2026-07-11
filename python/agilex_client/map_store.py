"""导出 VLM 用地平面图：PNG + yaml + meta.json。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .client import AgilexClient
from .coords import MapInfo


def export_vlm_map(
    client: AgilexClient,
    map_name: str,
    output_dir: str | Path,
    chassis_host: str,
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    info = client.get_map_info(map_name)
    png_bytes = client.get_map_png_bytes(map_name)

    png_path = output / "map.png"
    yaml_path = output / "map.yaml"
    meta_path = output / "meta.json"

    png_path.write_bytes(png_bytes)

    map_yaml = {
        "image": "map.png",
        "resolution": 1.0,
        "origin": [0.0, 0.0, 0.0],
        "width": info.width,
        "height": info.height,
        "frame_id": "agilex_map",
        "coordinate_mode": "image_pixel",
        "negate": 0,
        "occupied_thresh": 0.65,
        "free_thresh": 0.196,
    }
    yaml_path.write_text(
        yaml.safe_dump(map_yaml, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    meta = {
        "source_map_name": map_name,
        "chassis_host": chassis_host,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "png_path": str(png_path),
        "yaml_path": str(yaml_path),
        "map_info": {
            "width": info.width,
            "height": info.height,
            "coordinate_mode": "image_pixel",
            "chassis_metric": {
                "origin_x": info.origin_x,
                "origin_y": info.origin_y,
                "resolution": info.resolution,
            },
        },
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "png_path": str(png_path),
        "yaml_path": str(yaml_path),
        "meta_path": str(meta_path),
    }

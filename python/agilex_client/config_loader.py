"""定位 Lite_Agilex_API 项目根目录并加载配置。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def find_project_root() -> Path:
    env_root = os.environ.get("LITE_AGILEX_API_ROOT")
    if env_root:
        root = Path(env_root).resolve()
        if (root / "config" / "default.yaml").exists():
            return root
        raise FileNotFoundError(f"LITE_AGILEX_API_ROOT 无效: {env_root}")

    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "config" / "default.yaml").exists():
            return parent

    raise FileNotFoundError(
        "找不到项目根目录（需存在 config/default.yaml）。"
        "可设置环境变量 LITE_AGILEX_API_ROOT。"
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """将 override 递归合并到 base，override 优先。"""
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    """加载 default.yaml，再用 local.yaml 覆盖（仅覆盖已有字段）。"""
    root = find_project_root()
    default_path = root / "config" / "default.yaml"
    local_path = root / "config" / "local.yaml"

    with open(default_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if local_path.exists():
        with open(local_path, encoding="utf-8") as f:
            local_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, local_cfg)

    return cfg

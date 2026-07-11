"""定位 Lite_Agilex_API 项目根目录并加载配置。"""

from __future__ import annotations

import os
from pathlib import Path

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


def load_config() -> dict:
    root = find_project_root()
    config_path = root / "config" / "default.yaml"
    local_path = root / "config" / "local.yaml"
    if local_path.exists():
        config_path = local_path
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

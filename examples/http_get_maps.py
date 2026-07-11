#!/usr/bin/env python3
"""通过 RANGER HTTP API 登录并获取地图列表。"""
from __future__ import annotations

import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default.yaml"
if (ROOT / "config" / "local.yaml").exists():
    CONFIG_PATH = ROOT / "config" / "local.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def login(http_base: str, username: str, password: str) -> str:
    url = f"{http_base.rstrip('/')}/admin/login"
    resp = requests.post(
        url,
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("status"):
        raise RuntimeError(body.get("msg") or "登录失败")
    return body["data"]["accessToken"]


def get_map_list(http_base: str, token: str) -> list:
    url = f"{http_base.rstrip('/')}/api/map/get/all"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("status"):
        raise RuntimeError(body.get("msg") or "获取地图列表失败")
    return body.get("data") or []


def main() -> int:
    cfg = load_config()
    http_base = cfg["chassis"]["http_base"]
    auth = cfg["auth"]

    print(f"目标: {http_base}")
    print("登录中...")
    token = login(http_base, auth["username"], auth["password"])
    print("登录成功，获取地图列表...")
    maps = get_map_list(http_base, token)

    if not maps:
        print("（无地图或返回为空）")
    else:
        print(f"共 {len(maps)} 张地图:")
        for item in maps:
            name = item.get("name") or item.get("mapName") or item
            print(f"  - {name}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"HTTP 错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

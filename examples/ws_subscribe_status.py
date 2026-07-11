#!/usr/bin/env python3
"""订阅松灵 NAVIS WebSocket 机器人/任务状态（短跑演示）。"""
from __future__ import annotations

import json
import signal
import sys
import threading
import time
from pathlib import Path

import yaml
from websocket import WebSocketTimeoutException, create_connection

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default.yaml"
if (ROOT / "config" / "local.yaml").exists():
    CONFIG_PATH = ROOT / "config" / "local.yaml"

RUN = True


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def on_signal(*_args):
    global RUN
    RUN = False


def heartbeat_loop(ws, client_id: str, interval: float):
    while RUN:
        msg = {
            "op": "ping",
            "timeStamp": str(int(time.time() * 1000)),
            "id": client_id,
        }
        ws.send(json.dumps(msg, ensure_ascii=False).encode("utf-8"))
        time.sleep(interval)


def main() -> int:
    cfg = load_config()
    ws_url = cfg["api"]["ws_base"]
    client_id = cfg["client"]["ws_client_id"]
    interval = float(cfg["client"]["heartbeat_interval_sec"])

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    print(f"连接 {ws_url} ...")
    ws = create_connection(ws_url, timeout=10)
    if not ws.connected:
        print("WebSocket 连接失败", file=sys.stderr)
        return 1

    hb = threading.Thread(target=heartbeat_loop, args=(ws, client_id, interval), daemon=True)
    hb.start()

    for topic in ("/dash_board/robot_status", "/run_management/task_status", "/slam_status"):
        sub = {"op": "subscribe", "topic": topic}
        ws.send(json.dumps(sub, ensure_ascii=False).encode("utf-8"))
        print(f"已订阅 {topic}")

    print("接收消息（Ctrl+C 退出，最多 30s）...")
    deadline = time.time() + 30
    while RUN and time.time() < deadline:
        try:
            ws.settimeout(2)
            raw = ws.recv()
            print(raw[:500] + ("..." if len(raw) > 500 else ""))
        except WebSocketTimeoutException:
            continue

    ws.close()
    print("已断开")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

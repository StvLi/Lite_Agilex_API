"""浏览器可交互场地地图。"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from agilex_client import AgilexClient, load_config  # noqa: E402

app = FastAPI(title="Agilex Map Viewer")
_client: AgilexClient | None = None
_map_name: str = ""
_frame_id: str = "agilex_map"
_pending_init_pose: dict[str, float] | None = None


def _get_client() -> AgilexClient:
    global _client, _map_name, _frame_id
    if _client is None:
        cfg = load_config()
        chassis = cfg["chassis"]
        auth = cfg["auth"]
        debug = cfg["debug_site"]
        _map_name = debug["map_name"]
        _frame_id = debug["frame_id"]
        _client = AgilexClient(
            http_base=chassis["http_base"],
            ws_base=chassis["ws_base"],
            username=auth["username"],
            password=auth["password"],
        )
        _client.login()
        try:
            _client.switch_map(_map_name)
        except RuntimeError:
            # 底盘导航进行中时 switch_map 会返回「状态有误」，不影响读图与位姿
            pass
    return _client


@app.on_event("startup")
async def startup() -> None:
    _get_client()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    html_path = Path(__file__).with_name("index.html")
    return html_path.read_text(encoding="utf-8")


@app.get("/api/map")
async def get_map():
    client = _get_client()
    info = client.get_map_info(_map_name)
    png = client.get_map_png_bytes(_map_name)
    b64 = base64.b64encode(png).decode("ascii")
    return {
        "map_name": _map_name,
        "frame_id": _frame_id,
        "coordinate_mode": "image_pixel",
        "width": info.width,
        "height": info.height,
        "image_data_url": f"data:image/png;base64,{b64}",
    }


@app.post("/api/navigate")
async def navigate(payload: dict):
    client = _get_client()
    client.navigate_to_point(
        float(payload["x"]),
        float(payload["y"]),
        float(payload.get("theta_deg", 0.0)),
        follow_road_net=bool(payload.get("follow_road_net", False)),
    )
    return {"success": True}


@app.post("/api/init_pose")
async def init_pose(payload: dict):
    """记录初始位姿（像素），不立即下发底盘。需再调用 /api/start_localization。"""
    global _pending_init_pose
    _pending_init_pose = {
        "x": float(payload["x"]),
        "y": float(payload["y"]),
        "theta_deg": float(payload.get("theta_deg", 0.0)),
    }
    return {
        "success": True,
        **_pending_init_pose,
        "message": "已记录初始位姿，请调用 /api/start_localization 启动定位优化",
    }


@app.post("/api/start_localization")
async def start_localization(payload: dict):
    """拉起底盘定位优化。"""
    global _pending_init_pose
    client = _get_client()
    use_pending = bool(payload.get("use_pending_pose", True))
    if use_pending:
        if _pending_init_pose is None:
            raise RuntimeError("未设置初始位姿，请先调用 /api/init_pose")
        x = _pending_init_pose["x"]
        y = _pending_init_pose["y"]
        theta_deg = _pending_init_pose["theta_deg"]
    else:
        x = float(payload["x"])
        y = float(payload["y"])
        theta_deg = float(payload.get("theta_deg", 0.0))

    try:
        client.switch_map(_map_name)
    except RuntimeError:
        pass
    client.init_pose(x, y, theta_deg)
    result = {
        "success": True,
        "localized": False,
        "x": x,
        "y": y,
        "theta_deg": theta_deg,
        "message": "已下发初始位姿并启动定位优化",
    }
    if bool(payload.get("wait_for_ready", False)):
        timeout = float(payload.get("timeout_sec", 60.0))
        status = client.wait_for_localization(timeout_sec=timeout)
        result["localized"] = status.robot_nav_detail_status == 114
        result["nav_detail_status"] = status.robot_nav_detail_status
        result["message"] = (
            f"定位完成: {status.robot_nav_detail_status} "
            f"{status.robot_nav_detail_status_text}"
        )
    return result


@app.websocket("/ws/pose")
async def pose_stream(websocket: WebSocket):
    await websocket.accept()
    client = _get_client()

    try:
        import websockets

        url = f"{client.ws_base}/real_time_pose"
        async with websockets.connect(url) as ws:
            while True:
                raw = await ws.recv()
                msg = json.loads(raw)
                data = msg.get("data")
                if not data or "position" not in data:
                    continue
                await websocket.send_json(
                    {
                        "x": float(data["position"]["x"]),
                        "y": float(data["position"]["y"]),
                        "theta_deg": float(data.get("angle", 0.0)),
                    }
                )
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.close(code=1011, reason=str(exc))


def main() -> None:
    cfg = load_config()
    host = cfg["web"]["host"]
    port = int(cfg["web"]["port"])
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

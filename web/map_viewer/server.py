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
_map_info = None
_frame_id: str = "agilex_map"


def _get_client() -> AgilexClient:
    global _client, _map_name, _map_info, _frame_id
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
        _client.switch_map(_map_name)
        _map_info = _client.get_map_info(_map_name)
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
        "width": info.width,
        "height": info.height,
        "origin_x": info.origin_x,
        "origin_y": info.origin_y,
        "resolution": info.resolution,
        "image_data_url": f"data:image/png;base64,{b64}",
    }


@app.post("/api/navigate")
async def navigate(payload: dict):
    client = _get_client()
    client.navigate_to_point(
        float(payload["x"]),
        float(payload["y"]),
        float(payload.get("theta_deg", 0.0)),
        _map_info,
        follow_road_net=bool(payload.get("follow_road_net", False)),
    )
    return {"success": True}


@app.websocket("/ws/pose")
async def pose_stream(websocket: WebSocket):
    await websocket.accept()
    client = _get_client()
    info = client.get_map_info(_map_name)

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
                from agilex_client.coords import grid_to_world

                gx = float(data["position"]["x"])
                gy = float(data["position"]["y"])
                wx, wy = grid_to_world(gx, gy, info)
                await websocket.send_json(
                    {
                        "grid_x": gx,
                        "grid_y": gy,
                        "x": wx,
                        "y": wy,
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

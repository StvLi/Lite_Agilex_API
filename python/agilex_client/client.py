"""松灵智导 RANGER HTTP/WS 客户端。"""

from __future__ import annotations

import asyncio
import base64
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlencode

import requests

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

from .coords import MapInfo


@dataclass
class Pose2D:
    """地图图像像素系位姿（PNG 左上角为原点，y 向下）。"""

    x: float
    y: float
    theta_deg: float


@dataclass
class WorkStatus:
    map_name: str
    robot_status: int
    robot_nav_detail_status: int
    robot_nav_detail_status_text: str


# 底盘导航明细状态（摘自 RANGER API /real_time_work_status）
NAV_DETAIL_IDLE = 100
NAV_DETAIL_INIT_RUNNING = 110
NAV_DETAIL_INIT_SUCCESS = 111
NAV_DETAIL_INIT_FAILED = 112
NAV_DETAIL_LOCALIZING = 113
NAV_DETAIL_LOCALIZED = 114
NAV_DETAIL_LOCALIZE_FAILED = 115
NAV_DETAIL_LOCALIZE_LOST = 116
NAV_DETAIL_FAILURES = {
    NAV_DETAIL_INIT_FAILED,
    NAV_DETAIL_LOCALIZE_FAILED,
    NAV_DETAIL_LOCALIZE_LOST,
}


class AgilexClient:
    def __init__(
        self,
        http_base: str,
        ws_base: str,
        username: str,
        password: str,
        timeout: float = 30.0,
    ) -> None:
        self.http_base = http_base.rstrip("/")
        self.ws_base = ws_base.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._token: Optional[str] = None
        self._session = requests.Session()

    def login(self) -> str:
        url = f"{self.http_base}/admin/login"
        resp = self._session.post(
            url,
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("status"):
            raise RuntimeError(body.get("msg") or "登录失败")
        token = body["data"]["accessToken"]
        self._token = token
        return token

    def _headers(self) -> dict[str, str]:
        if not self._token:
            self.login()
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.http_base}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        resp = self._session.get(url, headers=self._headers(), timeout=self.timeout)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.status_code >= 400 or not body.get("status", False):
            raise RuntimeError(body.get("msg") or f"HTTP {resp.status_code}: {path}")
        return body

    def list_maps(self) -> list[dict[str, Any]]:
        body = self._get("/api/map/get/all")
        return body.get("data") or []

    def get_map_info(self, map_name: str) -> MapInfo:
        for item in self.list_maps():
            if item.get("name") == map_name:
                return MapInfo.from_api(map_name, item)
        raise KeyError(f"地图不存在: {map_name}")

    def get_map_png_bytes(self, map_name: str) -> bytes:
        url = f"{self.http_base}/api/map/get/png"
        resp = self._session.get(
            url,
            params={"mapName": map_name},
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("status"):
            raise RuntimeError(body.get("msg") or "获取地图 PNG 失败")
        data = body["data"]
        if isinstance(data, str):
            return base64.b64decode(data)
        raise RuntimeError("地图 PNG 数据格式异常")

    def switch_map(self, map_name: str) -> None:
        self._get("/api/nav/switch/map", {"mapName": map_name})

    def start_mapping(self, map_name: str, bag_record: bool = False) -> None:
        self._get(
            "/api/map/create/start",
            {"mapName": map_name, "bagRecord": str(bag_record).lower()},
        )

    def stop_mapping(self) -> None:
        self._get("/api/map/create/stop")

    def stop_and_save_mapping(self, remark: str = "") -> None:
        self._get("/api/map/create/save/stop", {"remark": remark})

    def _try_stop_navigation(self) -> None:
        try:
            self._get("/api/nav/task/stop")
        except RuntimeError:
            pass

    def navigate_to_point(
        self,
        x: float,
        y: float,
        angle_deg: float,
        follow_road_net: bool = False,
        sn: str = "",
    ) -> None:
        """下发任意点导航。x/y 为地图图像像素坐标。"""
        self._try_stop_navigation()
        params: dict[str, Any] = {
            "x": int(round(x)),
            "y": int(round(y)),
            "angle": int(round(angle_deg)) % 360,
            "type": "0",
            "followRoadNet": str(follow_road_net).lower(),
        }
        if sn:
            params["sn"] = sn
        self._get("/api/nav/task/point", params)

    def init_pose(self, x: float, y: float, angle_deg: float) -> None:
        """重定位。x/y 为地图图像像素坐标。"""
        self._get(
            "/api/nav/init/pose",
            {
                "x": int(round(x)),
                "y": int(round(y)),
                "angle": int(round(angle_deg)) % 360,
            },
        )

    def fetch_work_status_once(self) -> WorkStatus:
        if websockets is None:
            raise RuntimeError("需要安装 websockets 包")

        async def _recv() -> WorkStatus:
            url = f"{self.ws_base}/real_time_work_status"
            async with websockets.connect(url, open_timeout=self.timeout) as ws:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                    msg = json.loads(raw)
                    data = msg.get("data")
                    if not data:
                        continue
                    return WorkStatus(
                        map_name=str(data.get("mapName", "")),
                        robot_status=int(data.get("robotStatus", 0)),
                        robot_nav_detail_status=int(data.get("robotNavDetailStatus", 0)),
                        robot_nav_detail_status_text=str(
                            data.get("robotNavDetailStatusText", "")
                        ),
                    )

        return asyncio.run(_recv())

    def wait_for_localization(
        self,
        timeout_sec: float = 60.0,
        poll_interval_sec: float = 0.5,
    ) -> WorkStatus:
        """等待底盘完成初始化/定位优化，成功返回最终状态。"""
        deadline = time.time() + timeout_sec
        last_status: Optional[WorkStatus] = None
        while time.time() < deadline:
            status = self.fetch_work_status_once()
            last_status = status
            detail = status.robot_nav_detail_status
            if detail == NAV_DETAIL_LOCALIZED:
                return status
            if detail in NAV_DETAIL_FAILURES:
                raise RuntimeError(
                    f"定位失败: {detail} {status.robot_nav_detail_status_text}"
                )
            time.sleep(poll_interval_sec)
        if last_status is None:
            raise TimeoutError("等待定位状态超时：未收到工作状态")
        raise TimeoutError(
            "等待定位状态超时: "
            f"{last_status.robot_nav_detail_status} "
            f"{last_status.robot_nav_detail_status_text}"
        )

    def fetch_pose_once(self) -> Pose2D:
        if websockets is None:
            raise RuntimeError("需要安装 websockets 包")

        async def _recv() -> Pose2D:
            url = f"{self.ws_base}/real_time_pose"
            async with websockets.connect(url, open_timeout=self.timeout) as ws:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                    msg = json.loads(raw)
                    data = msg.get("data")
                    if data and "position" in data:
                        return Pose2D(
                            x=float(data["position"]["x"]),
                            y=float(data["position"]["y"]),
                            theta_deg=float(data.get("angle", 0.0)),
                        )

        return asyncio.run(_recv())

    def stream_pose(
        self,
        on_pose: Callable[[Pose2D], None],
        stop_event: threading.Event,
    ) -> None:
        if websockets is None:
            raise RuntimeError("需要安装 websockets 包")

        async def _loop() -> None:
            url = f"{self.ws_base}/real_time_pose"
            async with websockets.connect(url, open_timeout=self.timeout) as ws:
                while not stop_event.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue
                    msg = json.loads(raw)
                    data = msg.get("data")
                    if not data or "position" not in data:
                        continue
                    on_pose(
                        Pose2D(
                            x=float(data["position"]["x"]),
                            y=float(data["position"]["y"]),
                            theta_deg=float(data.get("angle", 0.0)),
                        )
                    )

        while not stop_event.is_set():
            try:
                asyncio.run(_loop())
            except Exception:
                if stop_event.is_set():
                    break
                time.sleep(1.0)

    def stream_laser_points(
        self,
        ws_path: str,
        on_points: Callable[[list[tuple[float, float]]], None],
        stop_event: threading.Event,
    ) -> None:
        """订阅底盘激光 WS，点坐标为地图图像像素 [x, y]。"""
        if websockets is None:
            raise RuntimeError("需要安装 websockets 包")

        async def _loop() -> None:
            path = ws_path if ws_path.startswith("/") else f"/{ws_path}"
            url = f"{self.ws_base}{path}"
            async with websockets.connect(url, open_timeout=self.timeout) as ws:
                while not stop_event.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue
                    msg = json.loads(raw)
                    data = msg.get("data")
                    if not isinstance(data, list):
                        continue
                    points: list[tuple[float, float]] = []
                    for item in data:
                        if not isinstance(item, (list, tuple)) or len(item) < 2:
                            continue
                        points.append((float(item[0]), float(item[1])))
                    if points:
                        on_points(points)

        while not stop_event.is_set():
            try:
                asyncio.run(_loop())
            except Exception:
                if stop_event.is_set():
                    break
                time.sleep(1.0)

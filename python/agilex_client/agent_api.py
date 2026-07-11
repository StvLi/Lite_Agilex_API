"""具身 Agent 可调用的 JSON 接口（地图 / 位姿 / 目标导航）。

设计原则：
- stdout 始终输出 JSON，便于 function calling 解析
- 优先走 ROS2 服务（桥接在跑时），否则回退 HTTP/WS 直连底盘
- 地图导出到固定缓存目录，便于文件系统读取
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .client import AgilexClient, Pose2D
from .config_loader import find_project_root, load_config
from .map_store import export_vlm_map


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("success") else 1)


def _fail(error_code: str, message: str, **extra: Any) -> None:
    _emit({"success": False, "error_code": error_code, "message": message, **extra})


def _run_ros2_python(root: Path, py_code: str, timeout: float = 30.0) -> tuple[int, str, str]:
    run_ros2 = root / "scripts" / "run_ros2.sh"
    proc = subprocess.run(
        [str(run_ros2), "python3", "-c", py_code],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _client_from_cfg(cfg: dict) -> AgilexClient:
    chassis = cfg["chassis"]
    auth = cfg["auth"]
    if not auth.get("username") or not auth.get("password"):
        raise RuntimeError("AUTH_MISSING: 请配置 config/local.yaml 的 auth 段")
    client = AgilexClient(
        http_base=chassis["http_base"],
        ws_base=chassis["ws_base"],
        username=auth["username"],
        password=auth["password"],
        timeout=float(cfg["network"]["http_timeout_sec"]),
    )
    client.login()
    return client


def _map_cache_dir(cfg: dict, root: Path) -> Path:
    rel = cfg.get("agent", {}).get("map_cache_dir", "data/agent_cache/current_map")
    return (root / rel).resolve()


def get_map(*, prefer_ros: bool = True) -> dict[str, Any]:
    """Function 0：获取当前调试地图 PNG + 元数据，写入固定缓存目录。"""
    root = find_project_root()
    cfg = load_config()
    debug = cfg["debug_site"]
    map_name = debug["map_name"]
    cache_dir = _map_cache_dir(cfg, root)

    if prefer_ros:
        out_dir = str(cache_dir)
        py = f"""
import json, rclpy
from agilex_msgs.srv import SaveDebugMap
rclpy.init()
node = rclpy.create_node('_agent_get_map')
cli = node.create_client(SaveDebugMap, '/agilex/save_debug_map')
if not cli.wait_for_service(timeout_sec=3.0):
    print(json.dumps({{"success": False, "error_code": "SERVICE_UNAVAILABLE"}}))
    raise SystemExit(2)
req = SaveDebugMap.Request()
req.map_name = {map_name!r}
req.output_dir = {out_dir!r}
fut = cli.call_async(req)
rclpy.spin_until_future_complete(node, fut, timeout_sec=60.0)
resp = fut.result()
print(json.dumps({{
    "success": bool(resp.success),
    "map_name": {map_name!r},
    "png_path": resp.png_path,
    "yaml_path": resp.yaml_path,
    "meta_path": resp.meta_path,
    "message": resp.message,
    "transport": "ros2",
}}))
node.destroy_node()
rclpy.shutdown()
"""
        code, stdout, stderr = _run_ros2_python(root, py, timeout=90.0)
        if code == 0 and stdout:
            data = json.loads(stdout.splitlines()[-1])
            if data.get("success"):
                return _enrich_map_payload(data, cache_dir, map_name)
        if code == 2:
            pass  # fall through to HTTP
        elif code != 0:
            return {
                "success": False,
                "error_code": "ROS_CALL_FAILED",
                "message": stderr or stdout or "save_debug_map 调用失败",
            }

    try:
        client = _client_from_cfg(cfg)
        paths = export_vlm_map(client, map_name, cache_dir, cfg["chassis"]["host"])
        info = client.get_map_info(map_name)
        return {
            "success": True,
            "map_name": map_name,
            "coordinate_mode": "image_pixel",
            "width": info.width,
            "height": info.height,
            "files": {
                "png": paths["png_path"],
                "yaml": paths["yaml_path"],
                "meta": paths["meta_path"],
            },
            "message": "ok",
            "transport": "http",
        }
    except Exception as exc:
        return {
            "success": False,
            "error_code": "GET_MAP_FAILED",
            "message": str(exc),
        }


def _enrich_map_payload(data: dict[str, Any], cache_dir: Path, map_name: str) -> dict[str, Any]:
    meta_path = Path(data.get("meta_path", ""))
    width = height = None
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        mi = meta.get("map_info", {})
        width = mi.get("width")
        height = mi.get("height")
    return {
        "success": True,
        "map_name": map_name,
        "coordinate_mode": "image_pixel",
        "width": width,
        "height": height,
        "files": {
            "png": data.get("png_path", ""),
            "yaml": data.get("yaml_path", ""),
            "meta": data.get("meta_path", ""),
        },
        "cache_dir": str(cache_dir),
        "message": data.get("message", "ok"),
        "transport": data.get("transport", "ros2"),
    }


def get_pose(*, prefer_ros: bool = True) -> dict[str, Any]:
    """Function 1：获取当前位姿（图像像素 x/y，朝向度）。"""
    root = find_project_root()
    cfg = load_config()
    frame_id = cfg["debug_site"]["frame_id"]

    if prefer_ros:
        py = """
import json, rclpy
from agilex_msgs.srv import GetChassisPose
rclpy.init()
node = rclpy.create_node('_agent_get_pose')
cli = node.create_client(GetChassisPose, '/agilex/get_pose')
if not cli.wait_for_service(timeout_sec=3.0):
    print(json.dumps({"success": False, "error_code": "SERVICE_UNAVAILABLE"}))
    raise SystemExit(2)
fut = cli.call_async(GetChassisPose.Request())
rclpy.spin_until_future_complete(node, fut, timeout_sec=15.0)
resp = fut.result()
print(json.dumps({
    "success": bool(resp.success),
    "x": float(resp.x),
    "y": float(resp.y),
    "theta_deg": float(resp.theta_deg),
    "frame_id": resp.frame_id,
    "coordinate_mode": "image_pixel",
    "message": resp.message,
    "transport": "ros2",
}))
node.destroy_node()
rclpy.shutdown()
"""
        code, stdout, stderr = _run_ros2_python(root, py, timeout=30.0)
        if code == 0 and stdout:
            return json.loads(stdout.splitlines()[-1])
        if code != 2:
            return {
                "success": False,
                "error_code": "ROS_CALL_FAILED",
                "message": stderr or stdout or "get_pose 调用失败",
            }

    try:
        client = _client_from_cfg(cfg)
        pose = client.fetch_pose_once()
        return {
            "success": True,
            "x": pose.x,
            "y": pose.y,
            "theta_deg": pose.theta_deg,
            "frame_id": frame_id,
            "coordinate_mode": "image_pixel",
            "message": "ok",
            "transport": "websocket",
        }
    except Exception as exc:
        return {
            "success": False,
            "error_code": "GET_POSE_FAILED",
            "message": str(exc),
        }


def set_target_pose(
    x: float,
    y: float,
    theta_deg: float,
    *,
    follow_road_net: bool = False,
    prefer_ros: bool = True,
) -> dict[str, Any]:
    """Function 2：设置目标位姿并下发导航（图像像素）。"""
    root = find_project_root()

    if prefer_ros:
        py = f"""
import json, rclpy
from agilex_msgs.srv import NavigateToPose
rclpy.init()
node = rclpy.create_node('_agent_nav')
cli = node.create_client(NavigateToPose, '/agilex/navigate_to_pose')
if not cli.wait_for_service(timeout_sec=3.0):
    print(json.dumps({{"success": False, "error_code": "SERVICE_UNAVAILABLE"}}))
    raise SystemExit(2)
req = NavigateToPose.Request()
req.x = float({x})
req.y = float({y})
req.theta_deg = float({theta_deg})
req.follow_road_net = {str(follow_road_net).lower()}
fut = cli.call_async(req)
rclpy.spin_until_future_complete(node, fut, timeout_sec=15.0)
resp = fut.result()
print(json.dumps({{
    "success": bool(resp.success),
    "target": {{"x": {x}, "y": {y}, "theta_deg": {theta_deg}}},
    "coordinate_mode": "image_pixel",
    "message": resp.message,
    "transport": "ros2",
}}))
node.destroy_node()
rclpy.shutdown()
"""
        code, stdout, stderr = _run_ros2_python(root, py, timeout=30.0)
        if code == 0 and stdout:
            return json.loads(stdout.splitlines()[-1])
        if code != 2:
            return {
                "success": False,
                "error_code": "ROS_CALL_FAILED",
                "message": stderr or stdout or "navigate_to_pose 调用失败",
            }

    try:
        cfg = load_config()
        client = _client_from_cfg(cfg)
        client.navigate_to_point(x, y, theta_deg, follow_road_net=follow_road_net)
        return {
            "success": True,
            "target": {"x": x, "y": y, "theta_deg": theta_deg},
            "coordinate_mode": "image_pixel",
            "message": "导航任务已下发",
            "transport": "http",
        }
    except Exception as exc:
        return {
            "success": False,
            "error_code": "NAVIGATE_FAILED",
            "message": str(exc),
            "target": {"x": x, "y": y, "theta_deg": theta_deg},
        }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Agilex 具身 Agent JSON 接口")
    parser.add_argument(
        "--no-ros",
        action="store_true",
        help="跳过 ROS2，直连底盘 HTTP/WS",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("get-map", help="Function 0: 获取地图到缓存目录")
    sub.add_parser("get-pose", help="Function 1: 获取当前位姿（像素）")

    nav = sub.add_parser("set-target-pose", help="Function 2: 下发目标导航（像素）")
    nav.add_argument("x", type=float)
    nav.add_argument("y", type=float)
    nav.add_argument("theta_deg", type=float)
    nav.add_argument("--follow-road-net", action="store_true")

    args = parser.parse_args(argv)
    prefer_ros = not args.no_ros

    if args.command == "get-map":
        _emit(get_map(prefer_ros=prefer_ros))
    elif args.command == "get-pose":
        _emit(get_pose(prefer_ros=prefer_ros))
    elif args.command == "set-target-pose":
        _emit(
            set_target_pose(
                args.x,
                args.y,
                args.theta_deg,
                follow_road_net=args.follow_road_net,
                prefer_ros=prefer_ros,
            )
        )


if __name__ == "__main__":
    main()

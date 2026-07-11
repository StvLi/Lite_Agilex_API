"""松灵底盘 ROS2 桥接节点。"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from agilex_msgs.srv import (
    GetChassisPose,
    NavigateToPose,
    SaveDebugMap,
    StartMapping,
    StopMapping,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))

from agilex_client import AgilexClient, export_vlm_map  # noqa: E402
from agilex_chassis_bridge.map_conversion import (  # noqa: E402
    png_bytes_to_occupancy_grid,
    theta_deg_to_quaternion,
)


def load_config() -> dict:
    config_path = ROOT / "config" / "default.yaml"
    local_path = ROOT / "config" / "local.yaml"
    if local_path.exists():
        config_path = local_path
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class ChassisBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("agilex_chassis_bridge")
        self.cfg = load_config()
        chassis = self.cfg["chassis"]
        auth = self.cfg["auth"]
        debug = self.cfg["debug_site"]
        ros_cfg = self.cfg["ros2"]

        self.frame_id = debug["frame_id"]
        self.map_name = debug["map_name"]
        self.output_dir = str(ROOT / debug["output_dir"])
        self.service_prefix = ros_cfg["service_prefix"].rstrip("/")

        self.client = AgilexClient(
            http_base=chassis["http_base"],
            ws_base=chassis["ws_base"],
            username=auth["username"],
            password=auth["password"],
            timeout=float(self.cfg["network"]["http_timeout_sec"]),
        )
        self.client.login()
        self.map_info = self.client.get_map_info(self.map_name)
        self.get_logger().info(f"已连接底盘，当前地图: {self.map_name}")

        self._latest_pose = None
        self._pose_lock = threading.Lock()
        self._stop_pose = threading.Event()
        self._pose_thread = threading.Thread(target=self._pose_worker, daemon=True)
        self._pose_thread.start()

        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
        )
        self.pose_pub = self.create_publisher(PoseStamped, ros_cfg["pose_topic"], 10)
        self.map_pub = self.create_publisher(OccupancyGrid, ros_cfg["map_topic"], qos)
        self.map_image_pub = self.create_publisher(Image, ros_cfg["map_image_topic"], qos)
        self._publish_map_once()

        self.create_service(
            SaveDebugMap,
            f"{self.service_prefix}/save_debug_map",
            self._handle_save_debug_map,
        )
        self.create_service(
            GetChassisPose,
            f"{self.service_prefix}/get_pose",
            self._handle_get_pose,
        )
        self.create_service(
            NavigateToPose,
            f"{self.service_prefix}/navigate_to_pose",
            self._handle_navigate,
        )
        self.create_service(
            StartMapping,
            f"{self.service_prefix}/start_mapping",
            self._handle_start_mapping,
        )
        self.create_service(
            StopMapping,
            f"{self.service_prefix}/stop_mapping",
            self._handle_stop_mapping,
        )
        self.create_timer(1.0, self._publish_latest_pose)

    def _make_map_msgs(self):
        png = self.client.get_map_png_bytes(self.map_name)
        return png_bytes_to_occupancy_grid(
            png,
            self.map_info,
            self.frame_id,
            self.get_clock().now().to_msg(),
        )

    def _publish_map_once(self) -> None:
        try:
            occ, img = self._make_map_msgs()
            self.map_pub.publish(occ)
            self.map_image_pub.publish(img)
            self.get_logger().info("已发布 /agilex/map 与 /agilex/map_image")
        except Exception as exc:
            self.get_logger().error(f"发布地图失败: {exc}")

    def _pose_worker(self) -> None:
        def on_pose(pose):
            with self._pose_lock:
                self._latest_pose = pose

        self.client.stream_pose(self.map_info, on_pose, self._stop_pose)

    def _publish_latest_pose(self) -> None:
        with self._pose_lock:
            pose = self._latest_pose
        if pose is None:
            return
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.pose.position.x = pose.x
        msg.pose.position.y = pose.y
        msg.pose.orientation = theta_deg_to_quaternion(pose.theta_deg)
        self.pose_pub.publish(msg)

    def _handle_save_debug_map(self, request, response):
        map_name = request.map_name or self.map_name
        output_dir = request.output_dir or self.output_dir
        try:
            paths = export_vlm_map(
                self.client,
                map_name,
                output_dir,
                self.cfg["chassis"]["host"],
            )
            self.map_info = self.client.get_map_info(map_name)
            self._publish_map_once()
            response.success = True
            response.png_path = paths["png_path"]
            response.yaml_path = paths["yaml_path"]
            response.meta_path = paths["meta_path"]
            response.message = f"已导出 {map_name}"
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_get_pose(self, _request, response):
        try:
            pose = self.client.fetch_pose_once(self.map_info)
            response.success = True
            response.x = pose.x
            response.y = pose.y
            response.theta_deg = pose.theta_deg
            response.frame_id = self.frame_id
            response.message = "ok"
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_navigate(self, request, response):
        try:
            self.client.navigate_to_point(
                request.x,
                request.y,
                request.theta_deg,
                follow_road_net=request.follow_road_net,
            )
            response.success = True
            response.message = "导航任务已下发"
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_start_mapping(self, request, response):
        map_name = request.map_name or self.map_name
        try:
            self.client.start_mapping(map_name, bag_record=request.bag_record)
            response.success = True
            response.message = f"建图已启动: {map_name}"
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_stop_mapping(self, request, response):
        try:
            if request.save_map:
                self.client.stop_and_save_mapping(request.remark)
                self.map_info = self.client.get_map_info(self.map_name)
                self._publish_map_once()
                response.message = "建图已停止并保存"
            else:
                self.client.stop_mapping()
                response.message = "建图已停止（未保存）"
            response.success = True
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def destroy_node(self) -> bool:
        self._stop_pose.set()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ChassisBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

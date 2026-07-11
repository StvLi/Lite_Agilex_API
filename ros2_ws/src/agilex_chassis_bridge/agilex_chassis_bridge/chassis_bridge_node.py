"""松灵底盘 ROS2 桥接节点。"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import rclpy
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, TransformStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image, PointCloud2
from tf2_ros import TransformBroadcaster

from agilex_msgs.srv import (
    GetChassisPose,
    NavigateToPose,
    SaveDebugMap,
    SetInitialPose,
    StartLocalization,
    StartMapping,
    StopMapping,
)

def _bootstrap_python_path() -> None:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        python_dir = parent / "python"
        if (parent / "config" / "default.yaml").exists() and python_dir.is_dir():
            if str(python_dir) not in sys.path:
                sys.path.insert(0, str(python_dir))
            return
    raise FileNotFoundError(
        "找不到 Lite_Agilex_API 项目根目录，请设置 LITE_AGILEX_API_ROOT"
    )


_bootstrap_python_path()

from agilex_client import (  # noqa: E402
    AgilexClient,
    NAV_DETAIL_LOCALIZED,
    Pose2D,
    export_vlm_map,
    find_project_root,
    load_config,
)
from agilex_chassis_bridge.laser_conversion import pixel_points_to_pointcloud2  # noqa: E402
from agilex_chassis_bridge.map_conversion import (  # noqa: E402
    pixel_pose_to_rviz,
    png_bytes_to_occupancy_grid,
    quaternion_to_theta_deg,
    rviz_pose_to_pixel,
    theta_deg_to_quaternion,
)


class ChassisBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("agilex_chassis_bridge")
        self.cfg = load_config()
        chassis = self.cfg["chassis"]
        auth = self.cfg["auth"]
        debug = self.cfg["debug_site"]
        ros_cfg = self.cfg["ros2"]

        self.frame_id = debug["frame_id"]
        self.robot_frame = "base_link"
        self.map_name = debug["map_name"]
        self.output_dir = str(find_project_root() / debug["output_dir"])
        self.service_prefix = ros_cfg["service_prefix"].rstrip("/")

        self.client = AgilexClient(
            http_base=chassis["http_base"],
            ws_base=chassis["ws_base"],
            username=auth["username"],
            password=auth["password"],
            timeout=float(self.cfg["network"]["http_timeout_sec"]),
        )
        if not auth.get("username") or not auth.get("password"):
            raise RuntimeError(
                "API 凭据未配置。请复制 config/local.yaml.example 为 config/local.yaml 并填入用户名密码。"
            )
        self.client.login()
        try:
            self.client.switch_map(self.map_name)
        except RuntimeError as exc:
            self.get_logger().warning(f"启动时切换地图跳过: {exc}")
        self.map_info = self.client.get_map_info(self.map_name)
        self.get_logger().info(f"已连接底盘，当前地图: {self.map_name}")

        self._latest_pose = None
        self._pending_init_pose: Pose2D | None = None
        self._pose_lock = threading.Lock()
        self._init_pose_lock = threading.Lock()
        self._stop_pose = threading.Event()
        self._pose_thread = threading.Thread(target=self._pose_worker, daemon=True)
        self._pose_thread.start()

        vis_cfg = self.cfg.get("visualization", {})
        self._laser_enabled = bool(vis_cfg.get("laser_enabled", True))
        self._laser_accumulate = bool(vis_cfg.get("laser_accumulate", False))
        self._laser_accumulate_max = int(vis_cfg.get("laser_accumulate_max_scans", 6))
        self._laser_buffers: dict[str, list[tuple[float, float]]] = {}
        self._laser_history: list[list[tuple[float, float]]] = []
        self._laser_lock = threading.Lock()
        self._stop_laser = threading.Event()
        self._laser_threads: list[threading.Thread] = []

        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
        )
        self.pose_pub = self.create_publisher(PoseStamped, ros_cfg["pose_topic"], 10)
        self.pose_rviz_pub = self.create_publisher(
            PoseStamped,
            ros_cfg.get("pose_rviz_topic", "/agilex/pose_rviz"),
            10,
        )
        self.init_pose_preview_pub = self.create_publisher(
            PoseStamped,
            ros_cfg.get("init_pose_preview_topic", "/agilex/init_pose_preview"),
            10,
        )
        self.map_pub = self.create_publisher(OccupancyGrid, ros_cfg["map_topic"], qos)
        self.map_image_pub = self.create_publisher(Image, ros_cfg["map_image_topic"], qos)
        self.laser_pub = self.create_publisher(
            PointCloud2,
            ros_cfg.get("laser_map_topic", "/agilex/laser_map"),
            10,
        )
        self.tf_broadcaster = TransformBroadcaster(self)
        self._publish_map_once()
        self._start_laser_workers()

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
        self.create_service(
            SetInitialPose,
            f"{self.service_prefix}/set_initial_pose",
            self._handle_set_initial_pose,
        )
        self.create_service(
            StartLocalization,
            f"{self.service_prefix}/start_localization",
            self._handle_start_localization,
        )
        self.create_subscription(
            PoseWithCovarianceStamped,
            ros_cfg.get("initial_pose_topic", "/initialpose"),
            self._on_initial_pose,
            10,
        )
        self.create_timer(1.0, self._publish_latest_pose)
        self.create_timer(1.0, self._publish_pending_init_pose_preview)
        laser_hz = float(vis_cfg.get("laser_publish_hz", 0.5))
        if self._laser_enabled and laser_hz > 0.0:
            self.create_timer(1.0 / laser_hz, self._publish_laser_map)

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

        self.client.stream_pose(on_pose, self._stop_pose)

    def _start_laser_workers(self) -> None:
        if not self._laser_enabled:
            self.get_logger().info("激光地图叠加已关闭（visualization.laser_enabled=false）")
            return
        sources = self.cfg.get("visualization", {}).get(
            "laser_sources",
            ["/real_time_laser/front", "/real_time_laser/back"],
        )
        for ws_path in sources:
            thread = threading.Thread(
                target=self._laser_worker,
                args=(str(ws_path),),
                daemon=True,
            )
            thread.start()
            self._laser_threads.append(thread)
        self.get_logger().info(
            f"激光 WS 订阅已启动: {sources}，发布 {self.laser_pub.topic_name} "
            f"@ {self.cfg.get('visualization', {}).get('laser_publish_hz', 0.5)} Hz"
        )

    def _laser_worker(self, ws_path: str) -> None:
        def on_points(points: list[tuple[float, float]]) -> None:
            with self._laser_lock:
                self._laser_buffers[ws_path] = points

        self.client.stream_laser_points(ws_path, on_points, self._stop_laser)

    def _publish_laser_map(self) -> None:
        with self._laser_lock:
            if not self._laser_buffers:
                return
            merged: list[tuple[float, float]] = []
            for points in self._laser_buffers.values():
                merged.extend(points)
            if not merged:
                return
            if self._laser_accumulate:
                self._laser_history.append(list(merged))
                if len(self._laser_history) > self._laser_accumulate_max:
                    self._laser_history = self._laser_history[-self._laser_accumulate_max :]
                merged = [pt for scan in self._laser_history for pt in scan]

        try:
            msg = pixel_points_to_pointcloud2(
                merged,
                self.map_info.height,
                self.frame_id,
                self.get_clock().now().to_msg(),
            )
            self.laser_pub.publish(msg)
        except Exception as exc:
            self.get_logger().warning(f"发布激光点云失败: {exc}")

    def _pixel_pose_to_rviz(self, pose) -> tuple[float, float, float]:
        """图像像素位姿 → RViz/TF 用的 ROS 地图坐标（y 向上）。"""
        x, y = pixel_pose_to_rviz(float(pose.x), float(pose.y), self.map_info.height)
        return x, y, float(pose.theta_deg)

    def _rviz_pose_to_pixel(self, x_rviz: float, y_rviz: float) -> tuple[float, float]:
        return rviz_pose_to_pixel(x_rviz, y_rviz, self.map_info.height)

    def _store_pending_init_pose(self, pose: Pose2D) -> None:
        with self._init_pose_lock:
            self._pending_init_pose = pose
        self._publish_init_pose_preview(pose)

    def _apply_init_pose_to_chassis(
        self,
        pose: Pose2D,
        *,
        wait_for_ready: bool = False,
        timeout_sec: float | None = None,
    ) -> tuple[bool, bool, int, str]:
        """调用底盘 GET /api/nav/init/pose 启动 SLAM 定位优化。"""
        try:
            self.client.switch_map(self.map_name)
        except RuntimeError as exc:
            self.get_logger().warning(f"切换地图跳过: {exc}")

        self.client.init_pose(pose.x, pose.y, pose.theta_deg)
        message = (
            f"已下发初始位姿到 SLAM: "
            f"x={pose.x:.1f}, y={pose.y:.1f}, theta={pose.theta_deg:.1f}°"
        )
        localized = False
        nav_detail_status = 0
        if wait_for_ready:
            timeout = timeout_sec
            if timeout is None or timeout <= 0.0:
                timeout = float(self.cfg["network"]["localization_timeout_sec"])
            status = self.client.wait_for_localization(timeout_sec=timeout)
            localized = status.robot_nav_detail_status == NAV_DETAIL_LOCALIZED
            nav_detail_status = status.robot_nav_detail_status
            message = (
                f"定位完成: status={nav_detail_status} "
                f"{status.robot_nav_detail_status_text}"
            )
        return True, localized, nav_detail_status, message

    def _dispatch_init_pose_async(self, pose: Pose2D, source: str) -> None:
        def _worker() -> None:
            try:
                _, _, _, message = self._apply_init_pose_to_chassis(pose)
                self.get_logger().info(f"{source}: {message}")
            except Exception as exc:
                self.get_logger().error(f"{source} 下发 SLAM 初值失败: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _get_pending_init_pose(self) -> Pose2D | None:
        with self._init_pose_lock:
            return self._pending_init_pose

    def _publish_init_pose_preview(self, pose: Pose2D) -> None:
        x, y, theta = self._pixel_pose_to_rviz(pose)
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.orientation = theta_deg_to_quaternion(theta)
        self.init_pose_preview_pub.publish(msg)

    def _on_initial_pose(self, msg: PoseWithCovarianceStamped) -> None:
        frame = msg.header.frame_id
        if frame and frame != self.frame_id:
            self.get_logger().warning(
                f"忽略 /initialpose：frame_id={frame}，期望 {self.frame_id}"
            )
            return
        px, py = self._rviz_pose_to_pixel(
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
        )
        theta = quaternion_to_theta_deg(msg.pose.pose.orientation)
        pose = Pose2D(x=px, y=py, theta_deg=theta)
        self._store_pending_init_pose(pose)
        self.get_logger().info(
            "RViz 初值已记录（像素）: "
            f"x={pose.x:.1f}, y={pose.y:.1f}, theta={pose.theta_deg:.1f}°"
        )
        self._dispatch_init_pose_async(pose, "RViz /initialpose")

    def _resolve_init_pose(
        self,
        use_pending_pose: bool,
        x: float,
        y: float,
        theta_deg: float,
    ) -> Pose2D:
        if use_pending_pose:
            pending = self._get_pending_init_pose()
            if pending is None:
                raise RuntimeError(
                    "未设置初始位姿。请先在 RViz 使用 2D Pose Estimate，"
                    f"或调用 {self.service_prefix}/set_initial_pose"
                )
            return pending
        return Pose2D(x=x, y=y, theta_deg=theta_deg)

    def _handle_set_initial_pose(self, request, response):
        try:
            pose = Pose2D(
                x=float(request.x),
                y=float(request.y),
                theta_deg=float(request.theta_deg),
            )
            self._store_pending_init_pose(pose)
            response.success = True
            response.message = (
                f"已记录初始位姿: x={pose.x:.1f}, y={pose.y:.1f}, "
                f"theta={pose.theta_deg:.1f}°"
            )
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_start_localization(self, request, response):
        try:
            pose = self._resolve_init_pose(
                request.use_pending_pose,
                float(request.x),
                float(request.y),
                float(request.theta_deg),
            )
            timeout = float(request.timeout_sec)
            if timeout <= 0.0:
                timeout = float(self.cfg["network"]["localization_timeout_sec"])
            success, localized, nav_detail_status, message = self._apply_init_pose_to_chassis(
                pose,
                wait_for_ready=request.wait_for_ready,
                timeout_sec=timeout if request.wait_for_ready else None,
            )
            response.success = success
            response.localized = localized
            response.nav_detail_status = nav_detail_status
            response.message = message
        except Exception as exc:
            response.success = False
            response.localized = False
            response.nav_detail_status = 0
            response.message = str(exc)
        return response

    def _publish_pending_init_pose_preview(self) -> None:
        pose = self._get_pending_init_pose()
        if pose is not None:
            self._publish_init_pose_preview(pose)

    def _publish_robot_tf(self, pose) -> None:
        x, y, theta = self._pixel_pose_to_rviz(pose)
        tf_msg = TransformStamped()
        tf_msg.header.stamp = self.get_clock().now().to_msg()
        tf_msg.header.frame_id = self.frame_id
        tf_msg.child_frame_id = self.robot_frame
        tf_msg.transform.translation.x = x
        tf_msg.transform.translation.y = y
        tf_msg.transform.translation.z = 0.0
        tf_msg.transform.rotation = theta_deg_to_quaternion(theta)
        self.tf_broadcaster.sendTransform(tf_msg)

    def _publish_latest_pose(self) -> None:
        with self._pose_lock:
            pose = self._latest_pose
        if pose is None:
            return
        stamp = self.get_clock().now().to_msg()

        pixel_msg = PoseStamped()
        pixel_msg.header.stamp = stamp
        pixel_msg.header.frame_id = self.frame_id
        pixel_msg.pose.position.x = pose.x
        pixel_msg.pose.position.y = pose.y
        pixel_msg.pose.orientation = theta_deg_to_quaternion(pose.theta_deg)
        self.pose_pub.publish(pixel_msg)

        x, y, theta = self._pixel_pose_to_rviz(pose)
        rviz_msg = PoseStamped()
        rviz_msg.header.stamp = stamp
        rviz_msg.header.frame_id = self.frame_id
        rviz_msg.pose.position.x = x
        rviz_msg.pose.position.y = y
        rviz_msg.pose.orientation = theta_deg_to_quaternion(theta)
        self.pose_rviz_pub.publish(rviz_msg)

        self._publish_robot_tf(pose)

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
            pose = self.client.fetch_pose_once()
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
        self._stop_laser.set()
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
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

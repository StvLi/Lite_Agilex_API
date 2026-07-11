# Lite Agilex API

松灵机器人 RANGER 智导二开接口集成仓库。从桌面开发机调用底盘 HTTP/WS API，并提供 ROS2 桥接、Web 交互地图与 VLM 平面图导出。

## 已实现功能

| # | 功能 | 组件 | 验证方式（见下文） |
| --- | --- | --- | --- |
| 1 | 底盘建图（启停/保存） | ROS2 `/agilex/start_mapping`、`/agilex/stop_mapping` | 步骤 6 |
| 2 | 开发机可交互场地地图 | Web UI `:8765` | 步骤 5 |
| 3 | ROS2 存储/更新 VLM 平面图 | ROS2 `/agilex/save_debug_map` | 步骤 7 |
| 4 | 一键获取当前位姿 | ROS2 `/agilex/get_pose` + 话题 `/agilex/pose` | 步骤 8 |
| 5 | 一键目标点导航 | ROS2 `/agilex/navigate_to_pose` | 步骤 9 |
| — | 底盘连通性检查 | `check_connectivity.sh` | 步骤 2 |
| — | HTTP 地图列表 | `examples/http_get_maps.py` | 步骤 3 |
| — | RViz2 地图+位姿可视化 | `run_rviz.sh` | 步骤 5 |

默认调试地图：`hacthon_hall`（可在 `config/default.yaml` 修改）。

## 仓库结构

```text
Lite_Agilex_API/
  environment.yml              # conda 环境 lite_agilex_api
  requirements.txt
  config/default.yaml            # 底盘地址、地图名、ROS 话题
  python/agilex_client/          # HTTP/WS 客户端、坐标转换、VLM 导出
  ros2_ws/src/
    agilex_msgs/               # 自定义 Service 定义
    agilex_chassis_bridge/     # ROS2 桥接节点 + RViz 配置
  web/map_viewer/              # 浏览器交互地图
  scripts/
    setup_conda_env.sh         # 创建/更新 conda 环境（含镜像回退）
    env.sh                     # 激活项目环境
    check_connectivity.sh
    build_ros_ws.sh
    run_bridge.sh              # ROS2 桥接节点
    run_map_viewer.sh          # Web 地图
    run_rviz.sh                # RViz2
  examples/
    http_get_maps.py
    ws_subscribe_status.py
  docs/                        # 硬件、调试记录、开发规划、官方 API
  data/maps/hacthon_hall/        # VLM 导出目录（gitignore）
```

## 环境配置

使用**独立 conda 环境** `lite_agilex_api`，勿在 `base` 或 `lite_ros2_env` 中安装本项目依赖。

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/setup_conda_env.sh
conda activate lite_agilex_api
# 或: source scripts/env.sh
```

镜像策略（`setup_conda_env.sh` 内置）：

- Conda 创建：USTC → 失败回退 Aliyun
- Pip 安装：清华 TUNA → 失败回退 Aliyun
- 环境已存在：跳过 conda update，仅 pip install（快速路径）

## ROS2 接口一览

前提：`export ROS_DOMAIN_ID=15`（与整车其他 ROS 节点一致）。

### 话题（发布）

| 话题 | 类型 | 频率 | 说明 |
| --- | --- | --- | --- |
| `/agilex/pose` | `geometry_msgs/PoseStamped` | 1 Hz | 机器人在 `agilex_map` 系下位姿 |
| `/agilex/map` | `nav_msgs/OccupancyGrid` | 启动时 + 保存后 | 当前调试地图，供 RViz |
| `/agilex/map_image` | `sensor_msgs/Image` | 启动时 + 保存后 | 地图灰度图 |

### 服务

| 服务 | 类型 | 说明 |
| --- | --- | --- |
| `/agilex/save_debug_map` | `agilex_msgs/SaveDebugMap` | 导出 PNG + yaml + meta.json 到 `data/maps/` |
| `/agilex/get_pose` | `agilex_msgs/GetChassisPose` | 同步获取当前 x/y/θ（米、度） |
| `/agilex/navigate_to_pose` | `agilex_msgs/NavigateToPose` | 下发任意点导航 |
| `/agilex/start_mapping` | `agilex_msgs/StartMapping` | 启动底盘建图 |
| `/agilex/stop_mapping` | `agilex_msgs/StopMapping` | 停止建图（可选保存） |

## 开发机逐步验证指南

以下在**桌面开发机** `stvli@192.168.88.12` 执行。每步通过后再进行下一步。

### 步骤 0：前置条件

- 开发机可 ping 通松灵底盘 `10.7.5.99`
- 底盘导航服务已启动（Jetson 上松灵智导在运行）
- 已安装：conda、ROS2 Jazzy、`colcon`

```bash
export ROS_DOMAIN_ID=15
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
```

### 步骤 1：创建 conda 环境

```bash
./scripts/setup_conda_env.sh
conda activate lite_agilex_api
python -c "import requests, websockets, yaml, PIL, numpy, fastapi; print('依赖 OK')"
```

**预期**：打印 `依赖 OK`，无 `ModuleNotFoundError`。

### 步骤 2：网络连通性

```bash
./scripts/check_connectivity.sh
```

**预期**：5 个 IP ping 通过；`http://10.7.5.99` HTTP 有响应（非连接超时）。

### 步骤 3：HTTP 登录与地图列表

```bash
python examples/http_get_maps.py
```

**预期**：登录成功，列出底盘已有地图，包含 `hacthon_hall`。

### 步骤 4：编译 ROS2 工作区

```bash
./scripts/build_ros_ws.sh
source ros2_ws/install/setup.bash
ros2 interface list | grep agilex_msgs
```

**预期**：`colcon build` 成功；能看到 `agilex_msgs/srv/SaveDebugMap` 等接口。

### 步骤 5：启动桥接 + 可视化（3 个终端）

**终端 A — ROS2 桥接**（保持运行）：

```bash
export ROS_DOMAIN_ID=15
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/run_bridge.sh
```

**预期日志**：`已连接底盘，当前地图: hacthon_hall`、`已发布 /agilex/map 与 /agilex/map_image`。

**终端 B — Web 交互地图**（保持运行）：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/run_map_viewer.sh
```

浏览器打开：**http://localhost:8765**

**预期**：

- 显示 `hacthon_hall` 平面图
- 蓝色箭头随底盘移动（约 1 Hz 更新）
- 点击地图 → 确认框 → 下发导航（**仅在安全区域测试**）

**终端 C — RViz2**（可选）：

```bash
export ROS_DOMAIN_ID=15
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/run_rviz.sh
```

**预期**：Fixed Frame = `agilex_map`，可见地图与机器人位姿。

**终端 D — 观察话题**（桥接运行中时）：

```bash
export ROS_DOMAIN_ID=15
source /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API/ros2_ws/install/setup.bash
ros2 topic echo /agilex/pose --once
```

**预期**：返回含 `position.x/y` 和 `orientation` 的 `PoseStamped`。

### 步骤 6：建图流程（需求 1，需现场推车）

> 仅在需要**新建或更新**场地地图时执行；已有 `hacthon_hall` 可跳过。

```bash
export ROS_DOMAIN_ID=15
source ros2_ws/install/setup.bash

# 启动建图（默认地图名来自 config）
ros2 service call /agilex/start_mapping agilex_msgs/srv/StartMapping \
  "{map_name: 'hacthon_hall', bag_record: false}"

# 遥控底盘缓慢覆盖场地 ...

# 停止并保存
ros2 service call /agilex/stop_mapping agilex_msgs/srv/StopMapping \
  "{save_map: true, remark: 'debug update'}"
```

**预期**：`success: true`；底盘 Web 界面可见更新后的地图。

### 步骤 7：导出 VLM 平面图（需求 3）

```bash
ros2 service call /agilex/save_debug_map agilex_msgs/srv/SaveDebugMap "{}"
```

**预期**：`success: true`，返回 `png_path`、`yaml_path`、`meta_path`。

**验证文件**：

```bash
ls -la data/maps/hacthon_hall/
# 应有 map.png  map.yaml  meta.json
cat data/maps/hacthon_hall/map.yaml
```

`map.yaml` 应含 `resolution: 0.05`、`origin`、`frame_id: agilex_map`。

### 步骤 8：获取当前位姿（需求 4）

```bash
ros2 service call /agilex/get_pose agilex_msgs/srv/GetChassisPose "{}"
```

**预期**：

```text
success: true
x: <float>    # 米
y: <float>
theta_deg: <float>   # 0–360
frame_id: agilex_map
```

### 步骤 9：目标点导航（需求 5）

> **安全提醒**：确认场地无障碍、急停可用；先在小范围、低速区域测试。

```bash
# 将 x/y/theta_deg 替换为安全区域内的实测值
ros2 service call /agilex/navigate_to_pose agilex_msgs/srv/NavigateToPose \
  "{x: 0.0, y: 0.0, theta_deg: 0.0, follow_road_net: false}"
```

**预期**：`success: true`，`message: 导航任务已下发`；底盘开始移动。

也可在 Web 地图（步骤 5）上点击目标点进行验证。

### 步骤 10：WebSocket 位姿订阅（可选）

```bash
conda activate lite_agilex_api
python examples/ws_subscribe_status.py
```

**预期**：30 秒内打印 `/dash_board/robot_status` 等订阅数据（旧版示例，端口需与 RANGER API 一致；主流程以 `real_time_pose` 为准）。

## 配置

编辑 `config/default.yaml`（或复制为 `config/local.yaml`）：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `chassis.host` | `10.7.5.99` | 松灵 Jetson |
| `auth.username/password` | `admin` / `agx12345` | API 登录 |
| `debug_site.map_name` | `hacthon_hall` | 调试场地地图 |
| `debug_site.output_dir` | `data/maps/hacthon_hall` | VLM 导出目录 |
| `ros2.domain_id` | `15` | ROS 域 ID |
| `web.port` | `8765` | Web 地图端口 |

硬件详情见 [docs/HARDWARE.md](docs/HARDWARE.md)。

## 官方文档（RANGER AIR/DELTA）

| 类型 | 中文 | 英文 |
| --- | --- | --- |
| 二次开发 API | http://120.79.88.220/ranger-air/api/index.html | http://120.79.88.220/ranger-air/api_en/index.html |
| 帮助手册 | http://120.79.88.220/ranger-air/help/index.html | http://120.79.88.220/ranger-air/help_en/index.html |

> 本车队底盘使用松灵智导 API，与 GitHub `agilexrobotics/Navis` 旧 Demo 不同。详见 [docs/OFFICIAL_DOC_LINKS.md](docs/OFFICIAL_DOC_LINKS.md)。

## 相关仓库

| 仓库 | 路径 | 关系 |
| --- | --- | --- |
| `Lite_Insta_Agilex_Slam` | `../Lite_Insta_Agilex_Slam` | 感知/SLAM |
| `lite_ros2` | `../lite_ros2` | 机器人本体控制 |
| `lite_moveit2` | `../lite_moveit2` | 机械臂规划 |

## 调试记录

过程记录见 [docs/DEBUG_LOG.md](docs/DEBUG_LOG.md)，开发规划见 [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md)。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `ModuleNotFoundError` | `conda activate lite_agilex_api` 或 `./scripts/setup_conda_env.sh` |
| `Missing Bearer` / 登录失败 | 检查 `config/default.yaml` 凭据；登录需 POST JSON |
| `ros2: command not found` | `source /opt/ros/jazzy/setup.bash` |
| RViz 无地图 | 确认 `run_bridge.sh` 在运行且 `ROS_DOMAIN_ID=15` |
| Web 地图无位姿 | 确认底盘 WS `:6060/real_time_pose` 可达 |
| conda 安装慢 | 脚本已内置 USTC/Aliyun 回退；环境存在时仅 pip |

# Lite Agilex API

松灵机器人 RANGER 智导二开接口集成仓库。从桌面开发机调用底盘 HTTP/WS API，并提供 ROS2 桥接、Web 交互地图与 VLM 平面图导出。

## 已实现功能

| # | 功能 | 组件 | 验证（见「快速上手」） |
| --- | --- | --- | --- |
| 1 | 底盘建图（启停/保存） | `cmd_start_mapping.sh` / `cmd_stop_mapping.sh` | 终端 D |
| 2 | 开发机可交互场地地图 | Web UI `:8765` | 终端 B |
| 3 | ROS2 存储/更新 VLM 平面图 | `cmd_save_debug_map.sh` | 终端 D |
| 4 | 一键获取当前位姿 | `cmd_get_pose.sh` + `/agilex/pose` | 终端 D |
| 5 | 一键目标点导航 | `cmd_navigate.sh` | 终端 D |
| — | 一次性环境准备 | `bootstrap_once.sh` | 首次 |

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
    env.sh                     # 激活项目 Python 环境
    bootstrap_once.sh            # 一次性：凭据检查 + conda + ROS2 编译
    run_ros2.sh                  # ROS2 环境包装（cmd_*.sh 内部使用）
    cmd_get_pose.sh              # 一键读位姿（像素）
    cmd_navigate.sh              # 一键导航
    cmd_save_debug_map.sh        # 一键导出 VLM 地图
    cmd_echo_pose.sh             # 一键 echo /agilex/pose
    cmd_start_mapping.sh
    cmd_stop_mapping.sh
    check_connectivity.sh
    ros2_env.sh                # 手动 source 用（一般用 cmd_*.sh 即可）
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

前提：

1. `export ROS_DOMAIN_ID=15`（与整车其他 ROS 节点一致）
2. **每个新终端**在调用 `ros2` 前执行：`source scripts/ros2_env.sh`（加载 `agilex_msgs` 等自定义接口）

> 若跳过第 2 步，`ros2 service call ... agilex_msgs/srv/...` 会报 **The passed service type is invalid**。

## 坐标系约定（图像像素）

所有地图相关交互（位姿读取、导航目标、Web 点击、VLM 导出）统一使用 **地图 PNG 图像像素坐标**：

| 轴 | 含义 |
| --- | --- |
| `x` | 向右增大，范围 `0 … width-1` |
| `y` | 向下增大，范围 `0 … height-1` |
| `theta_deg` | 朝向（度），与底盘 WebSocket 一致 |

- 原点：PNG **左上角**（与 VLM 看到的图像一致）
- `/agilex/pose`、`get_pose`、`navigate_to_pose`、Web `/api/navigate` 均使用上述像素坐标
- 底盘公制参数（`origin_x/y`、`resolution`）仅保存在 `meta.json` 的 `chassis_metric` 字段，供调试参考

### 话题（发布）

| 话题 | 类型 | 频率 | 说明 |
| --- | --- | --- | --- |
| `/agilex/pose` | `geometry_msgs/PoseStamped` | 1 Hz | 机器人在 `agilex_map` 系下位姿（**图像像素**） |
| `/agilex/map` | `nav_msgs/OccupancyGrid` | 启动时 + 保存后 | 当前调试地图（分辨率 1 像素），供 RViz |
| `/agilex/map_image` | `sensor_msgs/Image` | 启动时 + 保存后 | 地图灰度图 |

### 服务

| 服务 | 类型 | 说明 |
| --- | --- | --- |
| `/agilex/save_debug_map` | `agilex_msgs/SaveDebugMap` | 导出 PNG + yaml + meta.json 到 `data/maps/` |
| `/agilex/get_pose` | `agilex_msgs/GetChassisPose` | 同步获取当前 x/y/θ（**图像像素**、度） |
| `/agilex/navigate_to_pose` | `agilex_msgs/NavigateToPose` | 下发任意点导航 |
| `/agilex/start_mapping` | `agilex_msgs/StartMapping` | 启动底盘建图 |
| `/agilex/stop_mapping` | `agilex_msgs/StopMapping` | 停止建图（可选保存） |

## 快速上手（无脑复制粘贴）

以下命令在桌面开发机执行。**每段整段复制到对应终端**，脚本会自动处理 conda / ROS2 环境，无需手动 `activate` 或 `source`。

> **验证状态（2026-07-11）**：上下行数据（位姿读取、导航下发、Web 地图、VLM 导出）已初步打通；**运动精度与目标点准确性待进一步标定**。

### 首次一次（任意终端，只做一次）

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/bootstrap_once.sh
```

若提示要填凭据：

```bash
nano /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API/config/local.yaml
```

填好 `auth` 后**再跑一次** `bootstrap_once.sh`。

---

### 终端 A — 桥接（保持运行）

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/run_bridge.sh
```

等到：`已连接底盘，当前地图: hacthon_hall`、`已发布 /agilex/map 与 /agilex/map_image`。

`启动时切换地图跳过: 状态有误` 是**警告**（导航进行中常见），可忽略。

---

### 终端 B — Web 地图（A 在跑后再开）

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/run_map_viewer.sh
```

浏览器：**http://localhost:8765**

---

### 终端 C — RViz（可选）

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/run_rviz.sh
```

---

### 终端 D — 功能测试（A 在跑，每条独立粘贴）

读位姿（像素）：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_get_pose.sh
```

看话题一次：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_echo_pose.sh
```

导航到指定像素（**把数字换成 get_pose 读到的 x/y**）：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_navigate.sh 665 350 0
```

导航冒烟（不传参 = 自动读当前位姿再导航）：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_navigate.sh
```

导出 VLM 平面图：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_save_debug_map.sh
```

建图（需现场推车，一般可跳过）：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_start_mapping.sh
```

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
./scripts/cmd_stop_mapping.sh
```

---

### 预期结果

| 命令 | 成功标志 |
| --- | --- |
| `cmd_get_pose.sh` | `success=True`，`x/y` 为像素（如 `665.0, 350.0`） |
| `cmd_navigate.sh` | `success=True`，`导航任务已下发` |
| `cmd_save_debug_map.sh` | `success=True`，生成 `data/maps/hacthon_hall/map.png` |
| Web `:8765` | 地图 + 蓝色箭头约 1 Hz 更新 |

坐标均为 **PNG 图像像素**（左上角原点），不是米。

---

### 故障排除

| 现象 | 处理 |
| --- | --- |
| 终端 B `Application startup failed` | 先确保 A 在跑；仍失败则 `fuser -k 8765/tcp` 后重启 B |
| `waiting for service...` 一直等 | 终端 A 的 `run_bridge.sh` 没在跑 |
| `The passed service type is invalid` | 用 `cmd_*.sh`，不要裸跑 `ros2 service` |
| 登录失败 | 检查 `config/local.yaml` 的 `auth` |

---

## 开发机逐步验证指南（详细版）

以下为分项验证说明，日常操作以「快速上手」为准。

### 步骤 0：前置条件

- 开发机可 ping 通松灵底盘 `10.7.5.99`
- 底盘导航服务已启动（Jetson 上松灵智导在运行）
- 已安装：conda、ROS2 Jazzy、`colcon`

### 步骤 1–4：环境与编译

由 `./scripts/bootstrap_once.sh` 一次性完成（conda 依赖 + `colcon build`）。

可选冒烟：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
source scripts/env.sh
./scripts/check_connectivity.sh
python examples/http_get_maps.py
```

### 步骤 5–9

见上文「快速上手」终端 A/B/D。

### 步骤 10：WebSocket 位姿订阅（可选）

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
source scripts/env.sh
python examples/ws_subscribe_status.py
```

**预期**：30 秒内打印订阅数据（旧版示例；主流程以 `real_time_pose` 为准）。

## 配置

1. 复制凭据模板：`cp config/local.yaml.example config/local.yaml`
2. 编辑 `config/local.yaml`，**仅填写 `auth` 段**（用户名/密码）
3. `local.yaml` 会**覆盖** `default.yaml` 中的同名字段，其余参数（IP、地图名、ROS 话题等）仍从 `default.yaml` 继承
4. `local.yaml` 已加入 `.gitignore`，不会提交到 git

> **说明**：此前清理文档中的错误凭据时引入了 `local.yaml` 机制。之前能跑是因为凭据写在 `default.yaml` 里；现在凭据单独放 `local.yaml`，避免密码出现在代码库中。

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `chassis.host` | `10.7.5.99` | 松灵 Jetson API 地址 |
| `debug_site.map_name` | `hacthon_hall` | 调试场地地图 |
| `debug_site.output_dir` | `data/maps/hacthon_hall` | VLM 导出目录 |
| `ros2.domain_id` | `15` | ROS 域 ID |
| `web.port` | `8765` | Web 地图端口 |

硬件拓扑见 [docs/HARDWARE.md](docs/HARDWARE.md)（不含凭据）。

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
| `Missing Bearer` / 登录失败 | 检查 `config/local.yaml` 的 `auth`；登录需 POST JSON |
| `ros2: command not found` | 用 `cmd_*.sh` 或 `source scripts/ros2_env.sh` |
| RViz 无地图 | 确认 `run_bridge.sh` 在运行且 `ROS_DOMAIN_ID=15` |
| Web 地图启动失败 | 先开终端 A；或 `fuser -k 8765/tcp` 后重启 B |
| Web 地图无位姿 | 确认底盘 WS `:6060/real_time_pose` 可达 |
| `The passed service type is invalid` | 用 `cmd_*.sh`，不要裸跑 `ros2 service` |
| `navigate_to_pose` 失败 | 确认 `x/y` 为图像像素；桥接需在运行 |
| conda 安装慢 | 脚本已内置 USTC/Aliyun 回退；环境存在时仅 pip |

# 松灵二开接口调试记录

本文件按时间顺序记录调试过程、现象、结论与下一步。每次调试会话追加一节，不删除历史记录。

---

## 2026-07-11 — 项目初始化

### 目标

- 在 `src/Lite_Agilex_API` 建立独立仓库，封装松灵 NAVIS 二开接口调用。
- 首要能力：获取地图、定点导航、任务状态订阅。
- 与现有 `Lite_Insta_Agilex_Slam` 感知栈并行，底盘控制走 NAVIS API 而非直接 CAN/ugv_sdk。

### 上游参考

| 资源 | 地址 |
| --- | --- |
| 官方 API Demo | https://github.com/agilexrobotics/Navis |
| API 文档（本地副本待拉取） | `user_api.html`（仓库内浏览器打开） |

### 接口协议摘要（来自官方 Demo）

```text
HTTP  Base : http://<底盘IP>/apiUrl
WS    Base : ws://<底盘IP>:9090

典型流程：
  1. HTTP 登录获取 token
  2. WS 建立长连接，每 ~1s 发送心跳
  3. WS 订阅 /slam_status、/dash_board/robot_status、/run_management/task_status
  4. HTTP 获取地图列表 / 地图 PNG / map_info（含 origin、resolution）
  5. PNG 坐标 ↔ 地图真实坐标转换后下发导航任务
  6. HTTP run_realtime_task（单点）或 set_task + run_list_task（列表任务）
```

默认 API 目标机：`10.7.5.99`（松灵底盘 Jetson）。

### 待验证项

- [x] 从桌面开发机 `ping` / `ssh` 通 `10.7.5.99`
- [ ] HTTP `POST /user/passport/login` 返回有效 token（根路径曾返回 500，需用完整 login 路径验证）
- [ ] WS `:9090` 长连接 + 心跳稳定
- [ ] `GET /map_list` 返回已有地图
- [ ] `GET /downloadpng` + `GET /map_info` 可下载并解析地图
- [ ] `POST /realtime_task` 单点导航可执行
- [ ] 订阅 `/run_management/task_status` 可收到状态变化

### 计划调试顺序

1. **连通性** — `scripts/check_connectivity.sh`
2. **HTTP 登录 + 地图列表** — `examples/http_get_maps.py`
3. **WS 心跳 + 状态订阅** — `examples/ws_subscribe_status.py`
4. **定点导航冒烟** — `examples/navigate_to_point.py`（需现场确认安全区域）
5. **与 SLAM 栈坐标对齐** — 后续与 `Lite_Insta_Agilex_Slam` 对接

### 当前状态

- 仓库骨架、配置模板、脚本与示例已创建，Git 仓库已初始化（`src/Lite_Agilex_API`）。
- **2026-07-11 12:11** 首次连通性检查：全部节点 ping 通；`http://10.7.5.99/apiUrl` 返回 HTTP 500（服务可达，登录接口待验证）。

### 下一步

1. 在桌面开发机运行 `scripts/check_connectivity.sh`。
2. 确认 NAVIS 服务在 Jetson 上已启动（端口 9090 / HTTP）。
3. 拉取官方 `agilexrobotics/Navis` 到 `third_party/` 或 `vcs` 记录版本。
4. 完成 HTTP 登录与地图列表后，更新本节勾选状态。

---

## 2026-07-11 — 阅读官方 RANGER API 文档

### 文档来源

| 类型 | URL | 状态 |
| --- | --- | --- |
| API 中文 | http://120.79.88.220/ranger-air/api/index.html | 可读 |
| API 英文 | http://120.79.88.220/ranger-air/api_en/index.html | 可读 |
| 帮助中文 | http://120.79.88.220/ranger-air/help/index.html | 可读 |
| 帮助英文 | http://120.79.88.220/ranger-air/help_en/index.html | 可读 |

### 结论

- 官方文档为「松灵智导」RANGER AIR/DELTA 接口，共 **56** 个 HTTP/WS 端点。
- 与 GitHub `agilexrobotics/Navis` 旧 Demo **不是同一套 API**。
- 本地底盘 `10.7.5.99` 已验证匹配新 API：
  - `POST /admin/login` + JSON → 登录成功，返回 `accessToken`
  - `GET /api/map/get/all` + `Authorization` → 需 token（结构正确）
- 文档写登录为 GET，现场实现需 **POST JSON**（已实测）。

### 下一步

- [ ] 按 RANGER API 重写 `config/default.yaml` 与 `examples/`
- [ ] 实现 token 缓存与 `GET /api/map/get/all` 示例
- [ ] 验证 `GET /api/nav/task/point` 任意点导航（安全区域）

详见 [OFFICIAL_DOC_LINKS.md](OFFICIAL_DOC_LINKS.md)。

---

## 2026-07-11 — 切换为独立 conda 环境

### 变更

- 新增 `environment.yml`，环境名 **`lite_agilex_api`**
- `setup_venv.sh` 弃用，改由 `setup_conda_env.sh` 管理
- `run_bridge.sh` / `run_map_viewer.sh` / `build_ros_ws.sh` 自动 `source scripts/env.sh`

### 操作

```bash
./scripts/setup_conda_env.sh
conda activate lite_agilex_api
```

---

## 2026-07-11 — conda 环境依赖安装验证

### 镜像

- Pip 清华 TUNA 超时后回退 **Aliyun**（`https://mirrors.aliyun.com/pypi/simple/`）
- 快速路径：环境已存在时仅 `pip install -r requirements.txt`

### 验证结果

- `./scripts/setup_conda_env.sh` 成功
- 全部 Python 依赖 import 通过
- `examples/http_get_maps.py` 登录成功，返回 5 张地图
- `./scripts/build_ros_ws.sh` 编译 `agilex_msgs` + `agilex_chassis_bridge` 成功

---

## 2026-07-11 — Web 交互地图验证通过

### 环境

- 操作机：桌面开发机
- 底盘：`10.7.5.99`，地图 `hacthon_hall`
- 终端 A：`run_bridge.sh`；终端 B：`run_map_viewer.sh`

### 现象

- 曾出现 `web/__init__.py` 被误写为路径文本，导致 `python -m web.map_viewer.server` 报 `NameError: name 'web' is not defined`。
- 修复后 Web 地图显示正常：平面图、位姿箭头约 1 Hz 更新、点击导航可用。

### 修复

- `run_map_viewer.sh` 改为直接执行 `server.py`，`uvicorn.run(app)` 避免包路径导入。
- 补全 `web/__init__.py` 与 `web/map_viewer/__init__.py` 合法内容。

### 结论

- **需求 2（Web 交互地图）** 在开发机上验证通过。

---

## 2026-07-11 — get_pose 服务 CLI 报错

### 操作

```bash
ros2 service call /agilex/get_pose agilex_msgs/srv/GetChassisPose "{}"
```

### 现象

- 未 source 工作区时：`The passed service type is invalid`
- `ros2 interface show agilex_msgs/srv/GetChassisPose` → `Unknown package 'agilex_msgs'`

### 结论

- 非 srv 定义错误；新终端未加载 `ros2_ws/install/setup.bash`，`agilex_msgs` 未进入 `AMENT_PREFIX_PATH`。
- source 后服务调用正常，返回 `success: true` 及 x/y/θ。

### 修复

- 新增 `scripts/ros2_env.sh`（`ROS_DOMAIN_ID` + Jazzy + 工作区 overlay）。
- README / `run_bridge.sh` / `build_ros_ws.sh` 提示先 source 该脚本。

### 下一步

- 继续验证 `save_debug_map`、`navigate_to_pose`、RViz2 显示。

---

## 2026-07-11 — get_pose 服务验证通过

### 操作

```bash
source scripts/ros2_env.sh
ros2 service call /agilex/get_pose agilex_msgs/srv/GetChassisPose "{}"
```

### 现象

- 返回 `success: true`，`x/y/theta_deg` 与 Web 地图位姿箭头一致（约 1 Hz 更新）。
- 坐标系为 `agilex_map` 世界坐标（米），与 `/agilex/pose` 话题一致。

### 结论

- **需求 4（获取当前位姿）** ROS2 服务在开发机上验证通过。

### 下一步

- 验证 `navigate_to_pose` 任意点导航。

---

## 2026-07-11 — navigate_to_pose 500 错误修复

### 操作

```bash
ros2 service call /agilex/navigate_to_pose agilex_msgs/srv/NavigateToPose \
  "{x: -15.0, y: 3.6, theta_deg: 0.0, follow_road_net: false}"
```

### 现象

- 修复前：HTTP 500，`/api/nav/task/point` 直接传入世界坐标（米）浮点数。
- 实测底盘 API 要求 **栅格像素整数**；浮点或米制坐标均返回 500。

### 修复

- `agilex_client.navigate_to_point()`：`world_to_grid()` 后 `int(round())`，下发前自动 `task/stop`。
- ROS2 桥接 / Web 地图仍使用世界坐标（与 `get_pose` 一致），转换在客户端完成。

### 结论

- 世界坐标 `(-15.0, 3.6)` → 栅格 `(661, 350)` 后导航返回 `开启导航成功`。

---

## 2026-07-11 — 统一地图交互为图像像素坐标

### 背景

与 coworker 讨论后决定：所有地图相关交互（位姿输出、导航输入、Web、VLM 导出）统一为 **PNG 图像像素坐标**，便于 VLM 直接对照平面图调用。公制米制坐标不再作为对外接口。

### 约定

- 原点：PNG 左上角；x 向右、y 向下；`theta_deg` 不变
- `get_pose` / `/agilex/pose` / `navigate_to_pose` / Web API 全部使用像素
- VLM `map.yaml`：`resolution: 1.0`，`coordinate_mode: image_pixel`
- 底盘公制参数移至 `meta.json` → `chassis_metric`

### 后续

- [ ] delta 位置/朝向增量控制接口（精细调节，待实现）
- [ ] 导航运动精度与目标点准确性标定

---

## 2026-07-11 — RViz 地图/TF 显示修复

### 现象

- Fixed Frame `agilex_map does not exist`；AgilexMap `No map received`。
- Panel 插件问题已在前序 commit 修复。

### 原因

1. 桥接地图 QoS 为 `TRANSIENT_LOCAL`，RViz 配置为 `Volatile`，订阅不匹配。
2. 未发布 `agilex_map` → `base_link` TF，Fixed Frame 无法解析。
3. OccupancyGrid 未按 ROS 惯例 `flipud`（左下原点），Map 插件无法正确渲染。

### 修复

- 桥接节点增加 `tf2_ros` 广播（像素 y 转为 ROS y：`height - py`）。
- `chassis_map.rviz` 地图 QoS 改为 Transient Local；用 Axes+TF 显示机器人。
- `/agilex/pose` 仍为图像像素坐标（API 不变）。

---

## 2026-07-11 — 初步联调通过（上下行数据可用）

### 环境

- 操作机：桌面开发机；底盘 `10.7.5.99`；地图 `hacthon_hall`
- 终端 A：`run_bridge.sh`；终端 B：`run_map_viewer.sh`；终端 D：`cmd_*.sh`

### 结论

- **上行**：`get_pose`、Web 位姿箭头、`/agilex/pose` 均返回图像像素坐标，与 PNG 一致。
- **下行**：`navigate_to_pose`、Web 点击导航可下发任务并收到 `success=True`。
- **VLM 导出**：`cmd_save_debug_map.sh` 生成 `map.png` / `map.yaml`（`coordinate_mode: image_pixel`）。
- **待确认**：运动是否准确到达目标像素/朝向，需进一步现场标定。

### 修复（联调过程中）

- Web 地图在底盘导航进行中 `switch_map` 失败不再导致启动崩溃。
- 桥接 Ctrl+C 不再重复 `rcl_shutdown` 报错。
- 新增 `bootstrap_once.sh`、`cmd_*.sh`、`run_ros2.sh` 无脑启动脚本。

---

## 2026-07-11 — RViz 定位初值 + SLAM 优化流程

### 背景

底盘 SLAM 定位基于优化，启动前需给定合理初始位姿，否则易陷入局部最优。

### 实现

1. RViz **2D Pose Estimate** → `/initialpose` → 桥接缓存像素初值 → 绿色 `/agilex/init_pose_preview`
2. `/agilex/set_initial_pose` 服务 + `cmd_set_init_pose.sh`
3. `/agilex/start_localization` 服务 + `cmd_start_localization.sh`
   - 调用底盘 `GET /api/nav/init/pose`
   - 可选等待 WS `/real_time_work_status` 至 `robotNavDetailStatus=114`（定位成功）
4. Web API：`POST /api/init_pose`、`POST /api/start_localization`

### 验证命令

```bash
# 终端 A
./scripts/run_bridge.sh

# 终端 D
./scripts/cmd_set_init_pose.sh 665 350 90
./scripts/cmd_start_localization.sh --no-wait
./scripts/cmd_get_pose.sh
```

### TODO

- VLM 自动设初值（调用 set_initial_pose + start_localization）
- RViz Panel 一键启动定位按钮
- Web 地图页交互控件

---

## 调试记录模板（复制使用）

```markdown
## YYYY-MM-DD — 简短标题

### 环境
- 操作机：
- 目标机：
- 网络：

### 操作
（执行的命令或脚本）

### 现象
（原始输出、错误信息）

### 结论
（成功/失败原因）

### 下一步
（后续动作）
```

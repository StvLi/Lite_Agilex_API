# 松灵底盘调试场地 — 开发规划

Date: 2026-07-11  
Status: **已确认，实施中**（2026-07-11）

## 用户确认（2026-07-11）

| 选项 | 决定 |
| --- | --- |
| 调试场地地图 | 沿用现有 **`hacthon_hall`** |
| 交互 UI | **Web UI + RViz2** 都要 |
| 建图流程 | **ROS2 全封装**：开始/停止/保存建图 + 导出 VLM 平面图 |

## 需求对照

| # | 需求 | 实现方案（拟定） | API / 组件 |
| --- | --- | --- | --- |
| 1 | 使用底盘建立调试场地地图 | 底盘 SLAM 建图（API 或 Web UI）→ 保存为命名地图 | `GET /api/map/create/start`、`/stop`、`/create/save/stop` |
| 2 | 开发机可交互场地地图 | 浏览器 Web UI：显示 PNG、叠加机器人位姿、点击下发导航 | WS `:6060/real_time_pose` + HTTP 导航 |
| 3 | ROS2 触发存储/更新 VLM 平面图 | `~/save_debug_map` 服务：拉取 PNG + 元数据，写入固定目录 | `GET /api/map/get/png`、`/api/map/get/all` |
| 4 | 一键获取当前位姿 | `~/get_pose` 服务：返回 map 系 x/y/θ（米+度） | WS `/real_time_pose` + 栅格→世界坐标转换 |
| 5 | 一键设置目标导航 | `~/navigate_to_pose` 服务：下发任意点导航 | `GET /api/nav/task/point` |

## 技术基线（已验证）

```text
底盘 HTTP : http://10.7.5.99
底盘 WS   : ws://10.7.5.99:6060/<topic>
登录      : POST /admin/login  JSON  {"username":"admin","password":"..."}
鉴权      : Authorization: Bearer <accessToken>
坐标系    : 水平向右为 x 轴，航向角顺时针 0–360°
位姿 WS   : 返回栅格坐标 (pixel)，导航 API 使用世界坐标 (m)
```

现场已有地图：`test`, `4.7test`, `4.7-2`, `deepcybo`, `hacthon_hall`（分辨率均为 0.05 m/px）。

## 系统架构

```text
┌─────────────────────────────────────────────────────────┐
│  桌面开发机 (stvli@192.168.88.12)  ROS_DOMAIN_ID=15     │
│                                                         │
│  ┌──────────────────┐    ┌───────────────────────────┐  │
│  │ map_viewer (Web) │    │ agilex_chassis_bridge     │  │
│  │ :8765 浏览器交互  │◄──►│ rclpy 节点                │  │
│  └──────────────────┘    │  - save_debug_map (srv)   │  │
│                            │  - get_pose (srv)         │  │
│                            │  - navigate_to_pose (srv) │  │
│                            │  - /agilex/pose (pub 1Hz) │  │
│                            └───────────┬───────────────┘  │
└────────────────────────────────────────┼──────────────────┘
                                         │ HTTP + WS
┌────────────────────────────────────────┼──────────────────┐
│  松灵底盘 Jetson (10.7.5.99)           ▼                  │
│  松灵智导 NAVIS — 建图 / 定位 / 导航                     │
└─────────────────────────────────────────────────────────┘
```

## 仓库结构（规划）

```text
Lite_Agilex_API/
  config/default.yaml              # 底盘地址、地图名、存储路径
  python/agilex_client/            # 共享 HTTP/WS 客户端
    client.py                      # 登录、token 缓存、坐标转换
    map_store.py                   # PNG+yaml+meta 导出
  ros2_ws/src/
    agilex_msgs/                   # SaveDebugMap, GetChassisPose, NavigateToPose
    agilex_chassis_bridge/         # ROS2 桥接节点
  web/map_viewer/                  # 轻量交互地图（FastAPI + 静态前端）
  data/maps/debug_site/            # VLM 用地平面图（gitignore）
    map.png
    map.yaml                       # origin, resolution, size
    meta.json                      # 更新时间、来源地图名
  scripts/
    run_bridge.sh                  # 启动 ROS2 桥接
    run_map_viewer.sh              # 启动 Web 交互地图
```

## VLM 平面图输出格式

```yaml
# data/maps/debug_site/map.yaml
image: map.png
resolution: 0.05
origin: [-48.0509, -40.904, 0.0]   # 来自底盘 map 元数据
width: 1210
height: 1240
frame_id: agilex_map
```

附带 `meta.json` 记录 `source_map_name`、`exported_at`、`chassis_host`，供 VLM 流水线引用。

## 坐标转换

WS 位姿为栅格坐标 `(px, py)`；对外 ROS/ROS2 接口统一使用世界坐标 `(mx, my)`（米）。
底盘 HTTP 导航/重定位 API 内部使用栅格像素整数，`agilex_client` 会自动转换：

```python
world_x = px * resolution + origin_x
world_y = (height - py) * resolution + origin_y
# 反向：world_to_grid → 取整后调用 /api/nav/task/point
```

## 分阶段实施

### Phase 0 — 基础（已基本确定，可立即开始）

- [x] 文档与 API 调研
- [ ] 修正 `config/default.yaml`（RANGER API、端口 6060、admin 凭据）
- [ ] `python/agilex_client`：登录、Bearer token、地图列表/PNG、坐标转换
- [ ] `agilex_msgs` 定义三个 Service
- [ ] `agilex_chassis_bridge` 节点骨架

### Phase 1 — ROS2 接口（核心需求 3/4/5）

- [ ] `save_debug_map`：导出 PNG + yaml + meta 到 `data/maps/<name>/`
- [ ] `get_pose`：WS 取位姿 + 转世界坐标，返回 PoseStamped 等价字段
- [ ] `navigate_to_pose`：调用 `/api/nav/task/point`
- [ ] 发布 `/agilex/pose`（1Hz）供其他节点订阅

### Phase 2 — 交互地图（需求 2）

- [ ] Web UI：加载当前调试地图 PNG
- [ ] WS 实时叠加机器人位置与朝向箭头
- [ ] 点击地图 → 调用 navigate（可先直连 API，后接 ROS2 服务）
- [ ] `scripts/run_map_viewer.sh` 一键启动

### Phase 3 — 建图流程（需求 1）

- [ ] 文档化底盘 Web 建图 SOP
- [ ] （可选）ROS2 `start_mapping` / `stop_and_save_mapping` 服务
- [ ] 建图完成后自动 `switch_map` + 导出 VLM 平面图

## ROS2 接口草案

```text
# agilex_msgs/srv/SaveDebugMap.srv
string map_name        # 空则用 config 默认
string output_dir      # 空则用 data/maps/<map_name>
---
bool success
string png_path
string yaml_path
string message

# agilex_msgs/srv/GetChassisPose.srv
---
bool success
float64 x
float64 y
float64 theta_deg
string frame_id
string message

# agilex_msgs/srv/NavigateToPose.srv
float64 x
float64 y
float64 theta_deg
bool follow_road_net false
---
bool success
string message
```

调用示例（先 `source scripts/ros2_env.sh`）：

```bash
source scripts/ros2_env.sh
ros2 service call /agilex/save_debug_map agilex_msgs/srv/SaveDebugMap "{}"
ros2 service call /agilex/get_pose agilex_msgs/srv/GetChassisPose "{}"
ros2 service call /agilex/navigate_to_pose agilex_msgs/srv/NavigateToPose \
  "{x: 1.0, y: 2.0, theta_deg: 90.0, follow_road_net: false}"
```

## 待用户确认

~~1. **调试场地地图名称**~~ → **`hacthon_hall`**  
~~2. **交互 UI 形态**~~ → **Web + RViz2**  
~~3. **建图主导方式**~~ → **ROS2 全封装**

确认后立即进入 Phase 0–1 实现。

### Git 提交记录（2026-07-11）

```text
58aa63c feat: add interactive web map viewer with click-to-navigate
ffec9b3 feat: add ROS2 chassis bridge for map, pose, and navigation
83bfa0c feat: add agilex_client RANGER HTTP/WS library
576bde4 feat: scaffold Lite Agilex API repo with RANGER docs and dev plan
```

## 环境隔离

- Python 依赖统一安装在独立 conda 环境 **`lite_agilex_api`**
- 创建：`./scripts/setup_conda_env.sh`
- 激活：`conda activate lite_agilex_api` 或 `source scripts/env.sh`
- **禁止**在 `base` / `lite_ros2_env` 中为本项目 `pip install`

## 风险与注意事项

- WS 端口为 **6060**（非文档旧版 9090）；位姿为栅格坐标，必须转换。
- 登录实际需 **POST JSON**（文档写 GET 不可用）。
- 导航调试前确认场地安全、急停可用。
- `data/maps/` 不提交 git，仅保留目录结构与示例 yaml。

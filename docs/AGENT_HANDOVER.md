# 具身 Agent 交接文档（Function Calling）

Date: 2026-07-11

本文档面向**后续 Coding Agent / 具身 Agent 集成者**，说明如何配置 function calling，调用松灵底盘的地图、位姿与导航能力。

> 仓库路径示例：`/home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API`  
> 下文简称 **项目根**。

---

## 1. 前置条件

| 项 | 要求 |
| --- | --- |
| 环境 | `./scripts/bootstrap_once.sh` 已执行；`config/local.yaml` 已填 `auth` |
| 网络 | 开发机可访问底盘 `10.7.5.99`（HTTP + WS `:6060`） |
| ROS（推荐） | 终端 A 运行 `./scripts/run_bridge.sh`；`ROS_DOMAIN_ID=15` |
| 坐标系 | **图像像素**：PNG 左上角原点，x 向右，y 向下，θ 为度 |

无 ROS 桥接时，三个核心 function 仍可走 **HTTP/WS 直连**（脚本自动回退）。

---

## 2. 三个核心 Function（推荐绑定）

| ID | 能力 | 脚本（JSON stdout） | ROS2 服务（等价） |
| --- | --- | --- | --- |
| **0** | 一键获取地图 | `./scripts/agent_get_map.sh` | `/agilex/save_debug_map` |
| **1** | 一键获取当前位姿 | `./scripts/agent_get_pose.sh` | `/agilex/get_pose` |
| **2** | 一键设置目标位姿并导航 | `./scripts/agent_set_target_pose.sh X Y THETA` | `/agilex/navigate_to_pose` |

统一 CLI（等价）：

```bash
cd <项目根>
source scripts/env.sh
python -m agilex_client.agent_api get-map
python -m agilex_client.agent_api get-pose
python -m agilex_client.agent_api set-target-pose 665 350 90
```

- **成功**：exit code `0`，stdout 为 JSON  
- **失败**：exit code `1`，stdout 仍为 JSON（含 `error_code` / `message`）

---

## 3. Function Calling Schema（OpenAI / 通用工具格式）

### 3.0 `agilex_get_map`

```json
{
  "name": "agilex_get_map",
  "description": "获取当前调试场地地图 PNG 与元数据，写入固定缓存目录，返回绝对路径。坐标系为 image_pixel。",
  "parameters": { "type": "object", "properties": {}, "required": [] }
}
```

### 3.1 `agilex_get_pose`

```json
{
  "name": "agilex_get_pose",
  "description": "获取机器人在当前地图上的位姿：x/y 为 PNG 图像像素，theta_deg 为朝向（度）。",
  "parameters": { "type": "object", "properties": {}, "required": [] }
}
```

### 3.2 `agilex_set_target_pose`

```json
{
  "name": "agilex_set_target_pose",
  "description": "设置目标位姿并下发底盘导航。x/y 为 PNG 图像像素，theta_deg 为到达目标点时的朝向（度，0-359）。",
  "parameters": {
    "type": "object",
    "properties": {
      "x": { "type": "number", "description": "目标 x 像素" },
      "y": { "type": "number", "description": "目标 y 像素" },
      "theta_deg": { "type": "number", "description": "目标朝向（度）" }
    },
    "required": ["x", "y", "theta_deg"]
  }
}
```

### Coding Agent 实现模板

```python
import json, subprocess

ROOT = "/home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API"

def call_tool(script: str) -> dict:
    p = subprocess.run(
        [f"{ROOT}/scripts/{script}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
    )
    data = json.loads(p.stdout)
    if p.returncode != 0:
        raise RuntimeError(data.get("message", p.stderr))
    return data

# Function 0
map_result = call_tool("agent_get_map.sh")
png_path = map_result["files"]["png"]

# Function 1
pose = call_tool("agent_get_pose.sh")

# Function 2
subprocess.run(
    [f"{ROOT}/scripts/agent_set_target_pose.sh", "665", "350", "90"],
    cwd=ROOT, check=True,
)
```

---

## 4. 典型成功输出

### 4.0 get-map

```json
{
  "success": true,
  "map_name": "hacthon_hall",
  "coordinate_mode": "image_pixel",
  "width": 1210,
  "height": 1240,
  "files": {
    "png": "/home/stvli/.../Lite_Agilex_API/data/agent_cache/current_map/map.png",
    "yaml": "/home/stvli/.../map.yaml",
    "meta": "/home/stvli/.../meta.json"
  },
  "cache_dir": "/home/stvli/.../data/agent_cache/current_map",
  "message": "ok",
  "transport": "ros2"
}
```

**Agent 读图**：直接 `open(files["png"], "rb")` 或 PIL / cv2。  
**读元数据**：`json.load(open(files["meta"]))` → `map_info.width/height/coordinate_mode`。

固定缓存目录（配置项 `agent.map_cache_dir`）：

```text
data/agent_cache/current_map/
  map.png      # 与 VLM 所见一致
  map.yaml     # resolution=1.0, origin=[0,0,0], coordinate_mode=image_pixel
  meta.json    # 含 chassis_metric 公制参数（仅供参考）
```

### 4.1 get-pose

```json
{
  "success": true,
  "x": 665.0,
  "y": 350.0,
  "theta_deg": 90.0,
  "frame_id": "agilex_map",
  "coordinate_mode": "image_pixel",
  "message": "ok",
  "transport": "ros2"
}
```

### 4.2 set-target-pose

```json
{
  "success": true,
  "target": { "x": 665.0, "y": 350.0, "theta_deg": 90.0 },
  "coordinate_mode": "image_pixel",
  "message": "导航任务已下发",
  "transport": "ros2"
}
```

---

## 5. 数据获取路径对照

| 需求 | 推荐方式 | 备选 |
| --- | --- | --- |
| 地图 PNG | `agent_get_map.sh` → `files.png` | Web `GET /api/map`（需 `run_map_viewer.sh`） |
| 地图尺寸 | JSON `width/height` 或 `meta.json` | `config/default.yaml` → `debug_site.map_width/height` |
| 实时位姿 | `agent_get_pose.sh` | ROS topic `/agilex/pose`（1Hz，像素） |
| 下发导航 | `agent_set_target_pose.sh` | ROS `/agilex/navigate_to_pose` |
| VLM 长期存档 | `cmd_save_debug_map.sh` | 写入 `data/maps/hacthon_hall/` |

### ROS2 Topic（桥接运行时，供订阅型 Agent）

```bash
# 位姿（像素坐标，与 function 1 一致）
./scripts/run_ros2.sh ros2 topic echo /agilex/pose --once

# 地图（OccupancyGrid，resolution=1 像素）
./scripts/run_ros2.sh ros2 topic echo /agilex/map --once
```

> **注意**：`/agilex/pose_rviz` 为 RViz 内部坐标（y 向上），**勿**给 VLM/导航 function 使用。

---

## 6. 常见错误与 Debug

| 现象 | error_code / 日志 | 处理 |
| --- | --- | --- |
| `success: false`, 登录相关 | `AUTH_MISSING` / `GET_*_FAILED` 含 login | 检查 `config/local.yaml` 的 `auth` |
| `SERVICE_UNAVAILABLE` 后仍成功 | `transport: websocket/http` | 桥接未开；已自动回退直连，一般可继续 |
| `SERVICE_UNAVAILABLE` 且失败 | 桥接与直连均不可用 | 启动 `./scripts/run_bridge.sh`；`ping 10.7.5.99` |
| `The passed service type is invalid` | 裸跑 `ros2 service` | 必须用 `agent_*.sh` 或 `cmd_*.sh` |
| `waiting for service...` 卡住 | 桥接未运行 | 终端 A 启动 `run_bridge.sh` |
| `navigate` 失败 / HTTP 500 | `NAVIGATE_FAILED` | 确认 x/y 为**像素整数附近**；底盘是否在导航态 |
| `get_pose` 超时 | `GET_POSE_FAILED` | 检查 WS `ws://10.7.5.99:6060/real_time_pose` |
| 地图文件不存在 | `files.png` 路径无效 | 先调用 function 0；检查 `data/agent_cache/` 权限 |
| 坐标不对 | 数值像米制 | 必须使用 **image_pixel**；勿用 `/agilex/pose_rviz` |

### 冒烟测试（复制执行）

```bash
cd <项目根>

# 终端 A
./scripts/run_bridge.sh

# 终端 B
./scripts/agent_get_map.sh | jq .
./scripts/agent_get_pose.sh | jq .
./scripts/agent_set_target_pose.sh 665 350 0 | jq .
```

---

## 7. 与 SLAM 初值的区别（勿混淆）

| 能力 | 用途 | 接口 |
| --- | --- | --- |
| **set-target-pose**（本文 Function 2） | 导航到目标点 | `navigate_to_pose` / `/api/nav/task/point` |
| **设 SLAM 初值** | 定位优化起点 | RViz 2D Pose Estimate → `/api/nav/init/pose` |

Function 2 **不是** SLAM 重定位；若 Agent 需设初值，见 README「SLAM 定位优化流程」或 `agent_api` 后续扩展。

---

## 8. 相关文件索引

| 文件 | 说明 |
| --- | --- |
| `python/agilex_client/agent_api.py` | JSON 接口实现（ROS 优先 + HTTP 回退） |
| `scripts/agent_get_map.sh` | Function 0 |
| `scripts/agent_get_pose.sh` | Function 1 |
| `scripts/agent_set_target_pose.sh` | Function 2 |
| `config/default.yaml` | `agent.map_cache_dir`、`debug_site.*` |
| `config/local.yaml` | 凭据（gitignore） |
| `README.md` | 人类操作快速上手 |

---

## 9. 后续扩展 TODO

- [ ] VLM 设 SLAM 初值 → 封装 `set_initial_pose` + `start_localization`
- [ ] Agent 轮询导航完成状态（`/real_time_work_status`，114=到达）
- [ ] gRPC/HTTP 网关包装 `agent_api`（多机 Agent 远程调用）

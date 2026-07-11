# NAVIS 二开接口概览

Date: 2026-07-11

基于松灵官方仓库 [agilexrobotics/Navis](https://github.com/agilexrobotics/Navis) 整理。完整接口定义见上游 `user_api.html`。

## 通信模型

| 通道 | 地址模板 | 用途 |
| --- | --- | --- |
| HTTP | `http://<底盘IP>/apiUrl` | 登录、地图资源、任务下发 |
| WebSocket | `ws://<底盘IP>:9090` | 长连接、心跳、话题订阅/发布 |

## 通用流程

1. 创建 HTTP 与 WS 两个客户端。
2. WS 建立长连接后，**每约 1 秒**发送心跳（`op: ping`）。
3. WS 发送 `subscribe` 订阅所需话题，持续接收推送。
4. HTTP 用于获取地图 PNG 及 `map_info`（origin、resolution、gridHeight），完成坐标转换。
5. 无地图时先录包/建图；有地图后下发导航任务。
6. 通过 `realtime_task`（单点）或 `set_task` + `run_list_task`（多点列表）执行导航。

## HTTP 常用接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/user/passport/login` | 登录，返回 token |
| GET | `/map_list?page=1&limit=-1` | 地图列表 |
| GET | `/downloadpng?mapName=<name>` | 下载地图 PNG |
| GET | `/map_info?mapName=<name>` | 地图元信息（原点、分辨率等） |
| POST | `/realtime_task` | 实时单点/路径导航 |
| POST | `/set_task` | 设置列表任务 |
| POST | `/run_list_task` | 执行列表任务 |

请求头需携带 `Authorization: <token>`（登录后获得）。

### 实时单点任务示例结构

```json
{
  "loopTime": 1,
  "points": [{
    "position": { "x": 1.0, "y": 2.0, "theta": 90.0 },
    "isNew": false,
    "cpx": 0,
    "cpy": 0
  }],
  "mode": "point"
}
```

`mode` 为 `path` 时需设置多个路径点。

## WebSocket 常用操作

### 心跳

```json
{ "op": "ping", "timeStamp": "<ms>", "id": "<client-id>" }
```

### 订阅状态

| 话题 | 说明 |
| --- | --- |
| `/slam_status` | SLAM/定位状态 |
| `/dash_board/robot_status` | 机器人整机状态 |
| `/run_management/task_status` | 导航任务状态 |
| `/scan` | 2D 激光（导航开启后） |
| `/points_raw` | 3D 点云 |

### 建图 / 录包 / 导航控制

通过 `call_service` 调用 `/input/op`：

| op_type | 说明 |
| --- | --- |
| `record_data` | 录包 |
| `map_3d` | 3D 建图 |
| `map_2d` | 2D 建图 |
| `follow_line` | 启动/停止导航 |

### 取消导航

发布到 `/run_management/navi_task/cancel`。

### 重定位

发布到 `/initialpose`（`geometry_msgs/PoseWithCovarianceStamped`）。

## 坐标转换

地图 PNG 像素坐标与导航真实坐标需双向转换，依赖 `map_info` 中的：

- `originX`, `originY`
- `resolution`
- `gridHeight`

官方 Demo 提供 `png_coordinate_to_map` 与 `map_coordinate_to_png` 参考实现。

## Python 依赖

```text
python3 >= 3.6
requests
websockets
websocket-client
```

可选：`numpy`, `opencv-python`（图像/点云处理）。

## 注意事项

- 官方 Demo 主要在 Ubuntu 18.04 开发；本团队环境为 Ubuntu 24.04，接口协议本身与 OS 无关。
- WS 心跳不可中断，否则连接可能被服务端断开。
- 现场导航调试前确认安全区域与急停可用。
- API 登录凭据与底盘 SSH 凭据不同，见 `config/default.yaml`。

# Lite Agilex API

松灵机器人 NAVIS 二开接口集成仓库。用于从桌面开发机或车载算力侧调用底盘导航 API：获取地图、订阅状态、下发定点/列表导航任务。

## 范围

当前聚焦：

- HTTP API：登录、地图列表、地图 PNG/元信息、实时/列表导航任务
- WebSocket API：心跳、状态订阅、建图/录包/导航控制
- 连通性检查与调试记录

不在本仓库范围：

- Insta360 / VSLAM 感知栈（见 `Lite_Insta_Agilex_Slam`）
- Lite 上肢/全身 ROS 控制（见 `lite_ros2`）
- 底层 CAN/ugv_sdk 直接底盘驱动

## 仓库结构

```text
Lite_Agilex_API/
  README.md
  requirements.txt
  config/
    default.yaml          # API 端点与凭据（勿提交真实密码到公开远端）
  docs/
    HARDWARE.md           # 硬件配置（移交其他 Agent）
    DEBUG_LOG.md          # 调试过程记录（持续追加）
    API_OVERVIEW.md       # NAVIS 接口概览
  scripts/
    check_connectivity.sh
    setup_venv.sh
  examples/
    http_get_maps.py
    ws_subscribe_status.py
  vcs/
    external_repositories.md
```

## 快速开始

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API

# 1. 检查到松灵底盘的网络连通性
./scripts/check_connectivity.sh

# 2. 创建 Python 虚拟环境
./scripts/setup_venv.sh
source .venv/bin/activate

# 3. 获取地图列表（需底盘 NAVIS 服务在线）
python examples/http_get_maps.py
```

## 配置

编辑 `config/default.yaml` 中的底盘 IP 与 API 登录凭据。  
底盘默认地址：`10.7.5.99`（松灵 Jetson，详见 `docs/HARDWARE.md`）。

## 官方文档（RANGER AIR/DELTA）

| 类型 | 中文 | 英文 |
| --- | --- | --- |
| 二次开发 API | http://120.79.88.220/ranger-air/api/index.html | http://120.79.88.220/ranger-air/api_en/index.html |
| 帮助手册 | http://120.79.88.220/ranger-air/help/index.html | http://120.79.88.220/ranger-air/help_en/index.html |

> 本车队底盘使用松灵智导 API，与 GitHub `agilexrobotics/Navis` 旧 Demo 不同。详见 [docs/OFFICIAL_DOC_LINKS.md](docs/OFFICIAL_DOC_LINKS.md)。

## 相关仓库

| 仓库 | 路径 | 关系 |
| --- | --- | --- |
| `Lite_Insta_Agilex_Slam` | `../Lite_Insta_Agilex_Slam` | 感知/SLAM，坐标系后续需对齐 |
| `lite_ros2` | `../lite_ros2` | 机器人本体控制 |
| `lite_moveit2` | `../lite_moveit2` | 机械臂规划 |

## 调试记录

所有调试过程写入 [docs/DEBUG_LOG.md](docs/DEBUG_LOG.md)，按日期追加，不覆盖历史。

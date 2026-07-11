# RANGER AIR/DELTA 官方文档链接

Date: 2026-07-11

松灵智导（RANGER AIR/DELTA）二次开发文档，托管于公网文档服务器。

## 链接

| 类型 | 中文 | 英文 |
| --- | --- | --- |
| 二次开发 API | http://120.79.88.220/ranger-air/api/index.html | http://120.79.88.220/ranger-air/api_en/index.html |
| 帮助手册 | http://120.79.88.220/ranger-air/help/index.html | http://120.79.88.220/ranger-air/help_en/index.html |

## 可读性验证（2026-07-11）

- 四个 URL 均可从桌面开发机访问（HTTP 200）。
- API 文档为 apidoc 静态页，数据嵌入 `assets/main.bundle.js`。
- 帮助手册为 MkDocs 静态页，章节完整可读。

## 与旧版 NAVIS Demo 的差异

本车队底盘（`10.7.5.99`）使用的是 **松灵智导 RANGER API**，不是 GitHub `agilexrobotics/Navis` 那套 `/apiUrl` + `:9090` ROS-bridge 接口。

| 项目 | RANGER 智导 API | 旧 NAVIS Demo |
| --- | --- | --- |
| 登录 | `POST /admin/login` JSON | `POST /apiUrl/user/passport/login` |
| 鉴权 | `Authorization: <accessToken>` | `Authorization: <token>` |
| 地图列表 | `GET /api/map/get/all` | `GET /apiUrl/map_list` |
| 任意点导航 | `GET /api/nav/task/point?x=&y=&angle=`（**栅格像素整数**） | `POST /apiUrl/realtime_task` |
| WebSocket | `/real_time_pose` 等 | `ws://IP:9090` ROS 话题桥 |

## API 分组（共 56 个接口）

| 分组 | 数量 | 主要内容 |
| --- | --- | --- |
| 01.地图 | 9 | 建图启停、获取地图/PNG、清除代价地图 |
| 02.导航 | 2 | 切换地图、初始化位姿 |
| 03.导航任务 | 7 | 任意点导航、循线、暂停/恢复/停止 |
| 04.点 | 4 | 点位增删改查 |
| 05.路径 | 4 | 路径增删改查 |
| 06.路网 | 4 | 路网增删改查 |
| 07.虚拟墙 | 4 | 虚拟墙增删改查 |
| 08.bag包 | 2 | 建图 bag 管理 |
| 09.配置 | 5 | 电量阈值、语言、通用配置 |
| 10.其他 | 5 | 登录、改密、WiFi、操作日志 |
| 99.websocket | 10 | 位姿、地图、激光、底盘状态等推送 |

## 帮助手册要点

- 登录需 `POST /admin/login` + JSON，凭据配置在 `config/local.yaml`。
- 任务页支持：点位导航、重定位、任意点导航、切换地图。
- 高级页支持：地图/点/路网管理。
- 路网有方向性；导航时可选择沿路网或 A* 最短路径。

## 本地底盘实测（2026-07-11）

```bash
# 登录（凭据来自 config/local.yaml）
curl -X POST http://10.7.5.99/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<API用户名>","password":"<API密码>"}'
# 返回 accessToken

# 带 token 获取地图
curl http://10.7.5.99/api/map/get/all \
  -H "Authorization: <accessToken>"
```

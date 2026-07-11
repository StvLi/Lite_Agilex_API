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

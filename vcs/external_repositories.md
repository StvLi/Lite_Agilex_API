# External Repositories

Date: 2026-07-11

## Primary Upstream

```text
松灵 NAVIS API Demo:
https://github.com/agilexrobotics/Navis

分支: master
关键文件:
  - agilex_demo.py      Python 参考实现
  - user_api.html       完整 HTTP/WS 接口文档
  - src/                C++ Demo
```

建议拉取方式（本地 third_party，不提交大文件）：

```bash
cd /home/stvli/Desktop/where_is_my_key/src/Lite_Agilex_API
git clone --depth 1 https://github.com/agilexrobotics/Navis.git third_party/Navis
```

## Related Ecosystem

```text
底盘底层 SDK (CAN):
https://github.com/agilexrobotics/ugv_sdk

Python 底盘控制:
https://github.com/agilexrobotics/pyagxrobots

产品手册合集:
https://github.com/agilexrobotics/AgileX-Robotics-all-products-user-manuals
```

本仓库优先使用 NAVIS HTTP/WebSocket 二开接口，不直接依赖 ugv_sdk，除非 NAVIS 不可用。

## Sibling Repositories

| 仓库 | 路径 |
| --- | --- |
| `Lite_Insta_Agilex_Slam` | `../Lite_Insta_Agilex_Slam` |
| `lite_ros2` | `../lite_ros2` |
| `lite_moveit2` | `../lite_moveit2` |

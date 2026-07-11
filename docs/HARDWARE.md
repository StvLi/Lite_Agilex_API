# 硬件设备配置

Date: 2026-07-11

> 本文档仅记录硬件配置与登录凭据，供后续 Agent 接手时使用。  
> 不含软件栈、调试步骤或 API 说明。

## 设备清单

| 设备 | 架构 | 系统 | 用户名 | IP | 密码 |
| --- | --- | --- | --- | --- | --- |
| （车载）机器人运控（地瓜 RDK X5） | ARM | Ubuntu 24.04 | sunrise | 192.168.88.10 | sunrise |
| （车载）算力（DGX Spark） | ARM | Ubuntu 24.04 | deep | 192.168.88.11 | 123456 |
| 桌面开发机 | x86 | Ubuntu 24.04 | stvli | 192.168.88.12 / 10.7.5.100 | lpz20001018 |
| （车）松灵底盘（Jetson） | ARM | （待确认） | admin | 10.7.5.99 | agx12345 |

## 网络分段

```text
192.168.88.0/24   车载内部网段
  .10  RDK X5 运控
  .11  DGX Spark 算力
  .12  桌面开发机（局域网侧）

10.7.5.0/24       车辆/底盘网段
  .99  松灵底盘 Jetson（NAVIS 二开接口目标机）
  .100 桌面开发机（车辆网侧）
```

## SSH 快速参考

```bash
# 运控板
ssh sunrise@192.168.88.10

# 算力机
ssh deep@192.168.88.11

# 松灵底盘
ssh admin@10.7.5.99

# 本机开发环境
# 用户 stvli，工作区 /home/stvli/Desktop/where_is_my_key
```

## 角色说明

| 设备 | 角色 |
| --- | --- |
| RDK X5 | 机器人运控域控制器，后续与底盘/上肢协同 |
| DGX Spark | 车载算力，当前主要运行感知/SLAM（`Lite_Insta_Agilex_Slam`） |
| 桌面开发机 | 主开发与调试终端，可访问两个网段 |
| 松灵底盘 Jetson | 底盘运动与 NAVIS 导航栈，二开 HTTP/WebSocket API 宿主 |

## 共享约定

```text
ROS_DOMAIN_ID=15
```

所有参与 ROS2 通信的设备应保持一致（与 `Lite_Insta_Agilex_Slam` 项目相同）。

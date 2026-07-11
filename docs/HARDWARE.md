# 硬件设备配置

Date: 2026-07-11

> 本文档仅记录硬件拓扑与网络信息，供后续 Agent 接手时使用。  
> **登录凭据不写入文档**，统一放在 `config/local.yaml`（已 gitignore）。

## 设备清单

| 设备 | 架构 | 系统 | 用户名 | IP |
| --- | --- | --- | --- | --- |
| （车载）机器人运控（地瓜 RDK X5） | ARM | Ubuntu 24.04 | sunrise | 192.168.88.10 |
| （车载）算力（DGX Spark） | ARM | Ubuntu 24.04 | deep | 192.168.88.11 |
| 桌面开发机 | x86 | Ubuntu 24.04 | stvli | 192.168.88.12 / 10.7.5.100 |
| （车）松灵底盘（Jetson） | ARM | （待确认） | （见 local.yaml） | 10.7.5.99 |

## 网络分段

```text
192.168.88.0/24   车载内部网段
  .10  RDK X5 运控
  .11  DGX Spark 算力
  .12  桌面开发机（局域网侧）

10.7.5.0/24       车辆/底盘网段
  .99  松灵底盘 Jetson（二开 API 目标机）
  .100 桌面开发机（车辆网侧）
```

## SSH 快速参考

```bash
# 运控板
ssh <用户>@192.168.88.10

# 算力机
ssh <用户>@192.168.88.11

# 松灵底盘（用户名见 config/local.yaml）
ssh <用户>@10.7.5.99
```

## 凭据配置

```bash
cp config/local.yaml.example config/local.yaml
# 编辑 local.yaml 填入 SSH 与 API 登录凭据
```

## 角色说明

| 设备 | 角色 |
| --- | --- |
| RDK X5 | 机器人运控域控制器 |
| DGX Spark | 车载算力，感知/SLAM |
| 桌面开发机 | 主开发与调试终端 |
| 松灵底盘 Jetson | 底盘二开 HTTP/WebSocket API 宿主（底层闭源，仅通过 API 交互） |

## 共享约定

```text
ROS_DOMAIN_ID=15
```

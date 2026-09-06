## 套餐: 多协议数据中枢 {#standard}

部署一套轻量协议融合服务，把不同控制器统一成一套可读写的点位数据。

| 设备 | 用途 |
|------|------|
| reComputer R1000 / R1100 系列 | 将多种现场协议统一为点位模型和 MQTT 接口 |
| reTerminal DM 系列 | 运行相同服务，并通过本机触控屏操作 |
| 工业控制器 | 提供 OPC UA、Modbus、BACnet/IP 或 MQTT 数据 |

**部署完成后你可以：**
- 从一个入口配置 OPC UA、Modbus、BACnet/IP 和 MQTT 控制器
- 使用自动发现加快接入，发现不完整时手动填写点位兜底
- 在一个总表中读取、筛选和受控写入所有现场点位
- 让上层应用只对接一套带版本的 MQTT 数据、命令和回执主题

**前提条件：** Docker Engine 20.10 及以上 · 至少 4 GB 可用空间 · 能够访问目标控制器网络

## 步骤 1: 部署多协议数据中枢 {#gateway type=docker_deploy required=true config=devices/gateway.yaml}

启动协议融合与数据服务，并让点位配置、审计记录和模型在重启后继续保留。

### 部署目标 {#gateway_local type=local config=devices/gateway.yaml default=true}

部署到当前运行 SenseCraft Solution 的设备。

### 接线

![连接架构](gallery/architecture.svg)

1. 将当前设备接入与以太网控制器相同的可达网络。
2. 标准本机 Docker 配置不会挂载串口。如需 Modbus RTU，请使用串口设备部署配置；真实硬件验证完成前不要开启生产写控制。
3. 保留默认管理界面和 MQTT 端口，或在部署前选择未占用的主机端口。

BACnet/IP 广播发现可能无法穿过 Docker Desktop 的桥接网络。本机部署时可手动填写 BACnet 地址，或选择远程 Linux 目标进行网段发现。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 不可用 | 启动 Docker Desktop 或 Docker Engine 后重试 |
| 8280 或 1883 端口被占用 | 在部署表单中选择其他管理界面或 MQTT 主机端口 |
| 镜像下载失败 | 确认设备能够访问 `sensecraft-missionpack.seeed.cn`，并至少有 4 GB 可用空间 |
| 健康检查一直等待 | 查看 `docker logs missionpack-industrial-gateway`，并确认 `/readyz` 返回 HTTP 200 |

### 部署目标 {#gateway_edge type=remote device_name="reComputer R / reTerminal DM" config=devices/gateway.yaml}

通过 SSH 部署到控制器网络中的 reComputer R1000/R1100 系列或 reTerminal DM 设备。

### 接线

![连接架构](gallery/architecture.svg)

1. 将所选 reComputer R 或 reTerminal DM 网口连接到控制器网络，并记录设备 IP 地址。
2. 如需 Modbus RTU，请使用串口设备安装方式挂载 USB 转 RS-485 适配器；真实硬件验证完成前不要开启生产写控制。
3. 输入设备的 SSH 地址和凭据，然后开始部署。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查设备 IP、用户名、凭据和 SSH 服务 |
| 无法访问镜像仓库 | 检查 DNS 与防火墙是否允许访问 `sensecraft-missionpack.seeed.cn` |
| 管理界面打不开 | 放行所选管理端口，并确认容器健康 |
| BACnet 发现不到设备 | 选择 BACnet 所在网段的网卡，并确认广播没有被阻断 |

## 步骤 2: 配置统一接入与数据服务 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

打开管理界面，创建首个管理员账号，并把第一台现场控制器接入统一点位模型。

1. 创建首个管理员账号，无需注册令牌。
2. 打开 **接入**，点击 **添加**，选择 OPC UA、Modbus、BACnet/IP 或 MQTT，并配置控制器。
3. 在支持的协议上运行自动发现，审阅候选项，只确认需要的点位。发现不可用或不完整时改用手动配置。
4. 打开 **点位**，在授予写权限之前确认实时值与数据质量。
5. 打开 **数据服务**，配置内置 MQTT Broker，并查看点位、在线状态、命令与回执主题。
6. 如需预测，可打开预测插件导入 CSV 数据并配置输入/输出点位。

### 前置条件

步骤 1 的服务容器必须处于健康状态。首次创建管理员不需要注册令牌。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 等待步骤 1 报告健康，再确认所选管理界面端口 |
| 发现结果里缺少某个点位 | 改用手动点位配置兜底，并核对其协议地址 |
| 控制命令被拒绝 | 检查点位写权限、当前数据质量、安全规则和命令回执 |
| MQTT 控制不可用 | 启用 TLS 并配置具有控制权限的身份；明文模式只允许遥测 |

## 步骤 3: 北向上云并验证断网补传（待镜像发布后启用） {#northbound type=manual required=false}

> **本步骤在当前方案部署的镜像上跑不通。** 步骤 1 使用的已发布 tag `missionpack-knn:v1.6.7`
> 不含北向发布器，下面每一个调用都返回 HTTP 404。因此本步骤不带任何可执行配置、也不带验证，
> 只作为待构建镜像的参考资料。带该能力的镜像发布后，本步骤会恢复
> `config=devices/northbound_setup.yaml` 与 `verify=true`，下面的验证即为本步骤的验证。

把网关指向外部或云端 MQTT Broker，然后验证 Broker 断网时数据落盘缓存、重连后按序补传。如果步骤 2 的内置 Broker 是唯一消费方，可跳过本步骤。

### 前置条件

步骤 2 创建的管理员会话、一个可达且带 CA 证书的外部 MQTT Broker，以及包含北向上云能力的镜像 tag。

**镜像 tag 状态。** 本包当前使用的已发布 tag `sensecraft-missionpack.seeed.cn/solution/missionpack-knn:v1.6.7` **不包含**北向发布器。该能力在上游 `feature/northbound-publish`（`f831bae`）分支上，镜像**尚未构建、尚未 push**。它将使用的不可变 tag **待定**，不要用 `latest` 代替。在该 tag 发布之前，`GET /system/northbound-publish/status` 返回 HTTP 404，本步骤无法完成。

**端点。**

| 调用 | 用途 |
|------|------|
| `PUT /system/northbound-publish/config` | Broker 地址与端口、主题前缀、批量 flush 大小与间隔、spool 限额、TLS 材料。凭据只写，接口从不回显 |
| `POST /system/northbound-publish/start` | 建立连接并开始发布 |
| `POST /system/northbound-publish/stop` | 断开连接并发出 offline 状态消息 |
| `GET /system/northbound-publish/status` | 运行状态、连接状态、队列容量，以及是否已配置凭据 |
| `GET /system/runtime-metrics` | `northbound.spool` 计数：`queued`、`queued_bytes`、`dropped`、`replayed`、`oldest_age_seconds` |

**TLS。** 需 TLS 1.2 及以上并校验 CA 与主机名，双向 TLS 可选。除非运行档恰好是 `test` 或 `development`，否则明文传输一律拒绝，生产部署必须提供 CA 证书。

**主题。** `<前缀>/{gateway}/telemetry`（批量、QoS1、不 retain）、`<前缀>/{gateway}/sources/{source_id}/health`（QoS1、retain）、`<前缀>/{gateway}/status`（遗嘱、QoS1、retain）、`<前缀>/{gateway}/heartbeat`（QoS0、不 retain、不落盘缓存——补传一条过期心跳会向云端谎报活性）。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| `/system/northbound-publish/status` 返回 404 | 运行中的镜像早于该能力；核对 tag 并等待待构建镜像 |
| 启动时报传输错误 | 除 test/development 运行档外明文一律拒绝，请提供 TLS 材料 |
| 状态显示 running 但未 connected | 检查 Broker 可达性、凭据，以及 CA 证书是否与 Broker 证书链匹配 |
| `queued_bytes` 持续增长且不排空 | 链路仍未恢复，或已达 spool 上限开始淘汰旧批次；查看 `dropped` 与 `oldest_age_seconds` |
| Broker 重启后云端缺消息 | 请使用带持久化的 Broker 与持久订阅会话；纯内存 Broker 会丢弃在订阅者重新订阅之前到达的消息 |

### 部署完成

#### 快速验证（待镜像发布后启用）

这些检查需要待构建的镜像；在 `v1.6.7` 上第 1 条就会返回 HTTP 404。

1. `GET /system/northbound-publish/status` 返回 running、connected，且队列容量大于 0。
2. 云端订阅 `<前缀>/{gateway}/telemetry` 的消费者收到含 `schema_version`、`message_id`、`gateway_id` 和 `samples` 数组的 envelope。
3. 停掉 Broker。断网期间 `/system/runtime-metrics` 中的 `northbound.spool.queued` 与 `queued_bytes` 持续增长。
4. 重启 Broker。缓存批次按序补传，`northbound.spool.queued` 回到 0，`dropped` 没有增加。
5. 确认 retained 的 `<前缀>/{gateway}/status` 主题已翻回 online。

#### 运行容量 soak

上游仓库带有生成方案说明中那些数字的 `r14_capacity_soak.py` 压测台。要在自己的硬件上复现，把上游仓库克隆到目标设备后执行：

```
uv run python scripts/r14_capacity_soak.py --profile release \
  --evidence-root log/r14-capacity-evidence --run-id release-<UTC 时间戳>
```

`release` profile 跑 2,000 点、时长 24 小时，且要求 git 工作区干净才肯启动——任何未跟踪文件都会被判为源不冻结，包括文件拷贝留下的 macOS AppleDouble `._*` 文件。`capacity-smoke` 是同样形状的 180 s 快速档，`northbound-*` 系列则额外注入云 Broker 断网。只有 `verdict.json` 报告 `passed=true`、`failures=[]` 且 `exit_code=0` 才算通过。

#### 下一步

1. 按自己最坏情况的断网时长设置 spool 限额：参考压测台在约 350 events/s 时缓存速率为 60.1 KB/s。
2. 给云端消费方准备去重键——补传是有序的 at-least-once，重放沿用同一个 `message_id`。
3. 对 `northbound.spool.dropped` 与 `oldest_age_seconds` 设告警；`dropped` 增长意味着 spool 限额正在丢数据。

#### 协议能力边界

| 协议 | 当前边界 |
|------|----------|
| OPC UA | 数据源配置、浏览/手动点位、实时读取和受控写入 |
| Modbus TCP | 手动点位、站号扫描、实时读取和受控写入 |
| BACnet/IP | Who-Is 发现、手动点位、ReadProperty，以及带优先级的 WriteProperty 与 Null 释放。**未实现** COV 订阅、BBMD/外部设备注册和 MS-TP |
| MQTT 数据源 | 明确的主题映射与有界的主题观察 |
| Modbus RTU/RS-485 | 已包含配置与通讯能力；需要串口设备部署配置和 USB 硬件验证 |
| 北向 MQTT 上云 | 批量遥测、retained 健康与状态、心跳，以及基于 SQLite 的落盘缓存与有序 at-least-once 补传。需要待构建镜像 tag，`v1.6.7` 不含 |
| 北向主题契约 | MissionPack v1 原生主题；当前版本未实现 Sparkplug B |

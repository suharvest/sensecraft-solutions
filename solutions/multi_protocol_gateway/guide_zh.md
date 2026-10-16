## 套餐: 多协议数据中枢 {#standard}

把 OPC UA、Modbus、BACnet/IP 和 MQTT 控制器接入同一套点位数据，在一个界面里读取和受控写入，并通过 MQTT 主题提供数据、命令和回执。

- **设备：** 运行服务的主机或 reComputer R1000 / R1100 / reTerminal DM；提供 OPC UA、Modbus、BACnet/IP 或 MQTT 数据的工业控制器。
- **软件：** Docker Engine 20.10 及以上，至少 4 GB 可用空间。
- **网络：** 主机能访问控制器网络和 `sensecraft-missionpack.seeed.cn`。

## 步骤 1: 部署多协议数据中枢 {#gateway type=docker_deploy required=true config=devices/gateway.yaml}

启动协议接入与数据服务。

### 部署目标 {#gateway_local type=local config=devices/gateway.yaml default=true}

部署到当前运行 SenseCraft Solution 的设备。在 Docker Desktop 上 BACnet/IP 广播发现可能不可用，需要手动填写 BACnet 地址，或改用远程部署。

### 接线

![连接架构](gallery/architecture.svg)

1. 将当前设备接入控制器所在网络。
2. 保留默认管理界面（8280）和 MQTT（1883）端口，或在部署表单中改为未占用的端口。
3. 本机部署不挂载串口；需要 Modbus RTU 时使用串口设备部署配置，硬件验证完成前不要开启生产写控制。

### 故障排查

| 现象 | 处理 |
|------|------|
| Docker 不可用 | 启动 Docker Desktop 或 Docker Engine 后重试 |
| 8280 或 1883 端口被占用 | 在部署表单中选择其他端口 |
| 镜像下载失败 | 确认设备能访问 `sensecraft-missionpack.seeed.cn`，至少有 4 GB 可用空间 |
| 健康检查一直等待 | 执行 `docker logs missionpack-industrial-gateway` 查看原因 |

### 部署目标 {#gateway_edge type=remote device_name="reComputer R1000 / R1100 / reTerminal DM" config=devices/gateway.yaml}

通过 SSH 部署到控制器网络中的 reComputer R1000 / R1100 或 reTerminal DM。reTerminal DM 可以直接在本机触控屏上操作。

### 接线

![连接架构](gallery/architecture.svg)

1. 将设备网口接入控制器网络，记录设备 IP。
2. 需要 Modbus RTU 时，接上 USB 转 RS-485 适配器并使用串口设备部署配置；硬件验证完成前不要开启生产写控制。
3. 输入设备的 SSH 地址和凭据，开始部署。

### 故障排查

| 现象 | 处理 |
|------|------|
| SSH 连接失败 | 检查设备 IP、用户名、凭据和 SSH 服务 |
| 无法访问镜像仓库 | 检查 DNS 与防火墙是否允许访问 `sensecraft-missionpack.seeed.cn` |
| 管理界面打不开 | 在设备防火墙放行管理端口，确认容器健康 |
| BACnet 发现不到设备 | 选择 BACnet 所在网段的网卡，确认广播没有被阻断 |

## 步骤 2: 配置统一接入与数据服务 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

打开管理界面，创建管理员账号，接入第一台控制器。

1. 创建首个管理员账号，不需要注册令牌。
2. 打开 **接入**，点击 **添加**，选择 OPC UA、Modbus、BACnet/IP 或 MQTT，配置控制器。
3. 运行自动发现，只确认需要的点位；发现不可用或不完整时手动添加点位。
4. 打开 **点位**，确认实时值与数据质量后再授予写权限。

### 前置条件

步骤 1 的服务处于健康状态。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面无法加载 | 等步骤 1 报告健康，再核对管理界面端口 |
| 发现结果里缺少某个点位 | 手动添加该点位并核对协议地址 |
| 控制命令被拒绝 | 检查点位写权限、数据质量、安全规则和命令回执 |
| MQTT 控制不可用 | 启用 TLS 并配置有控制权限的身份；明文模式只允许遥测 |

### 部署完成

#### 后续步骤

- 打开 **数据服务**，配置内置 MQTT Broker，查看点位、在线状态、命令与回执主题。
- 需要预测时，打开预测插件导入 CSV 数据并配置输入/输出点位。

## 步骤 3: 北向上云并验证断网补传（待镜像发布后启用） {#northbound type=manual required=false}

把网关数据发到外部或云端 MQTT Broker，Broker 断网时数据缓存在本地，重连后按序补传。只用步骤 2 的内置 Broker 时跳过本步骤。

### 前置条件

> **当前部署的镜像 `v1.6.7` 不包含此功能，本步骤暂时无法完成**，下面的接口都会返回 HTTP 404。

- 步骤 2 的管理员账号。
- 一个可访问的外部 MQTT Broker 及其 CA 证书。需要 TLS 1.2 及以上；生产环境不允许明文连接。
- 在管理接口中完成配置和启动：`PUT /system/northbound-publish/config`（Broker 地址、主题前缀、缓存上限、TLS 证书），`POST /system/northbound-publish/start`。

### 故障排查

| 现象 | 处理 |
|------|------|
| `/system/northbound-publish/status` 返回 404 | 当前镜像不含此功能 |
| 启动时报传输错误 | 提供 TLS 证书，生产环境不允许明文 |
| 状态显示 running 但未 connected | 检查 Broker 可达性、凭据，以及 CA 证书是否匹配 Broker 证书 |
| `queued_bytes` 持续增长且不排空 | 链路仍未恢复，或缓存已满开始丢弃旧数据；查看 `dropped` 与 `oldest_age_seconds` |
| Broker 重启后云端缺消息 | 使用带持久化的 Broker 和持久订阅会话 |

### 部署完成

#### 快速验证（待镜像发布后启用）

1. `GET /system/northbound-publish/status` 返回 running、connected。
2. 云端订阅 `<前缀>/{gateway}/telemetry`，能收到含 `message_id`、`gateway_id` 和 `samples` 的消息。
3. 停掉 Broker，`/system/runtime-metrics` 中的 `northbound.spool.queued` 持续增长。
4. 重启 Broker，`northbound.spool.queued` 回到 0，`dropped` 没有增加。
5. `<前缀>/{gateway}/status` 主题恢复为 online。

#### 运行容量 soak

在目标设备上克隆上游仓库后执行：

```
uv run python scripts/r14_capacity_soak.py --profile release \
  --evidence-root log/r14-capacity-evidence --run-id release-<UTC 时间戳>
```

`release` 档运行 24 小时，`capacity-smoke` 档运行 180 s。`verdict.json` 报告 `passed=true` 即通过。

#### 下一步

1. 按最长断网时长设置缓存上限。
2. 云端消费方按 `message_id` 去重，补传的消息可能重复。
3. 对 `northbound.spool.dropped` 与 `oldest_age_seconds` 设告警。

#### 协议能力边界

| 协议 | 当前边界 |
|------|----------|
| OPC UA | 数据源配置、浏览/手动点位、实时读取和受控写入 |
| Modbus TCP | 手动点位、站号扫描、实时读取和受控写入 |
| BACnet/IP | Who-Is 发现、手动点位、ReadProperty，以及带优先级的 WriteProperty 与 Null 释放。**不支持** COV 订阅、BBMD/外部设备注册和 MS-TP |
| MQTT 数据源 | 明确的主题映射与有界的主题观察 |
| Modbus RTU/RS-485 | 需要串口设备部署配置和 USB 硬件验证 |
| 北向 MQTT 上云 | 批量遥测、健康与状态、心跳、断网缓存与有序补传。`v1.6.7` 不含 |
| 北向主题契约 | MissionPack v1 主题；不支持 Sparkplug B |

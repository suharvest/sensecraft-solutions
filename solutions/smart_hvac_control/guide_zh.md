## 套餐: 标准部署 {#default}

部署暖通设定值预测与控制服务，接入 Eastron SDM630 电能表，先在观察模式下调试，读回、回滚和告警在自己的机组上验证通过、安全限值经工程师批准后再开启写入。

- **设备：** reComputer R1100 或任意 Docker 主机；Eastron SDM630 电能表（Modbus TCP 或 RS-485）；暖通控制器（OPC UA、Modbus 或 BACnet/IP），只做演练时可用内置模拟器。
- **软件：** Docker Engine 20.10 及以上，约 1 GB 可用磁盘，主机 8280 与 4841 端口空闲。
- **数据：** 至少一周的历史运行数据（CSV 或 Excel）。
- **限制：** 本系统不是安全认证的控制系统，机组自身的联锁与安全控制仍然生效。写入限值出厂为占位值（18–30 °C、每 5 分钟 1 °C、off/fan/cool/heat/auto 模式白名单），需现场工程师批准。本方案不提供节能率数据。

## 步骤 1: 部署暖通控制服务 {#hvac type=docker_deploy required=true config=devices/deploy.yaml}

部署预测与控制服务，填写电表、控制模式、安全限值和告警参数。

### 前置条件

- 电表的通讯方式与站号；暖通控制器的 OPC UA 地址（保留默认地址则连接内置模拟器）。
- **控制模式**保持 *observe*。工程师批准限值前，**安全基线批准人**留空。

### 部署目标 {#hvac_local type=local config=devices/deploy.yaml default=true}

部署到当前运行 SenseCraft Solution 的设备，用于连接内置模拟器演练，或本机能访问机组网络时使用。本目标不支持 Modbus RTU。

### 接线

1. 把本机接入暖通控制器和电表（或其 Modbus TCP 网关）所在网络。
2. 电表走 Modbus TCP；需要 RS-485 时改用远程部署。
3. 确认 8280 与 4841 端口空闲。

### 故障排查

| 现象 | 处理 |
|------|------|
| Docker 未运行 | 启动 Docker Desktop 或 Docker Engine 后重试 |
| 端口 8280 被占用 | 释放该端口 |
| 容器启动后退出 | 执行 `docker logs missionpack_knn`，最后几行是失败原因 |
| 网页打不开 | 等待约 30 s 服务启动完成 |
| 电表点位能读但数值明显不对 | 字节序或字序不匹配，见步骤 3 |

### 部署目标 {#hvac_remote type=remote config=devices/deploy.yaml}

通过 SSH 部署到机组网络中的 reComputer R1100 或其他 Linux 设备。电表接 RS-485，或工作机访问不到控制器网络时使用。

### 接线

1. 把设备网口接入控制器网络，记录 IP 地址。
2. 走 Modbus RTU 时接上 USB 转 RS-485 适配器（通常为 `/dev/ttyUSB0`），并使用串口设备部署配置。
3. RS-485 的波特率、校验位和站号与电表设置一致；不一致时表现为超时。

### 故障排查

| 现象 | 处理 |
|------|------|
| SSH 连接失败 | 检查设备 IP、用户名、凭据，以及 sshd 是否在运行 |
| 远程设备无 Docker | 先在设备上安装 Docker Engine |
| 部署超时 | 检查设备能否访问镜像仓库 |
| 网页打不开 | 在设备防火墙上放行 8280 端口 |
| 容器内看不到 `/dev/ttyUSB0` | 改用串口设备部署配置重新部署 |

## 步骤 2: 打开控制面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

打开控制台，创建首个管理员账号，确认步骤 1 配置的数据源在线。

### 前置条件

步骤 1 的服务处于健康状态。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认步骤 1 已完成 |
| 主机/端口错误 | 远程部署时把地址换成设备 IP |
| 某个数据源显示离线 | 检查可达性与站号；走 RS-485 时检查波特率和接线极性 |

## 步骤 3: 电表、控制链路与告警调试 {#commissioning type=manual required=true verify=true config=devices/commissioning.yaml}

注册电表，在观察模式下运行预测，逐项触发故障验证回滚和告警，全部通过后再开启写入。

### 前置条件

- 步骤 2 的管理员账号；能看到电表本机显示；一位熟悉本机组的操作人员审阅推荐值。
- 执行 `docker inspect -f '{{.Config.Image}}' missionpack_knn` 查看镜像版本。`v1.6.5` 不含 SDM630 模板、回滚和告警功能，只能完成观察模式部分。

### 打开写后核实（回滚）

写后核实默认关闭。在控制台创建预测运行时加上 `rollback` 段：

```json
{
  "schema_version": "prediction-run.v3",
  "interval_seconds": 60,
  "rollback": { "enabled": true, "settle_seconds": 2.5 }
}
```

`settle_seconds`（0–30，默认 1.0）必须大于数据源的采集间隔，否则会误报读回不一致。只核实 Modbus 点位，BACnet 输出不核实。

### 故障排查

| 现象 | 处理 |
|------|------|
| 电表模板导入被拒绝 | 模板最多 256 行，精简自定义模板 |
| 电压和频率看着合理但数值不对 | 在部署表单里切换浮点字序后重新读取 |
| 进口电能出现倒退 | 切换字序；或检查是否有两个数据源用不同站号轮询同一台电表 |
| 写入有 ACK 但读回始终不通过 | 检查点位质量，质量不为 good 时读回不会通过 |
| 回滚本身失败 | 会产生 critical 级 compensation-failed 告警。人工恢复机组，查清原因前不要重新开启写入 |
| 同一故障每次都开出新告警 | 对比两条告警的数据源与点位 id |

### 部署完成

#### 快速验证

1. `docker inspect -f '{{.Config.Image}}' missionpack_knn` 返回的是你打算运行的版本。
2. SDM630 的十个点位全部可读，电压、频率和进口电能与电表本机显示一致。
3. 进口有功电能只增不减，数据源重启后保持累计值。
4. 观察模式下跑完一个完整人流周期的预测，推荐值经机组操作人员审阅。
5. 安全限值已填入批准人姓名，基线不再报告为未批准。
6. 一次限值范围内的写入产生了命令回执，读回在容差内，点位质量为 good。
7. 数据源离线、读回不一致、样本过期三类故障各自产生预期告警，前两类各触发一次回滚。
8. 启用了北向上云时，`GET /system/runtime-metrics` 中的 `northbound.spool.queued` 为 0 且 `dropped` 未增加。

#### 需要导出的证据

交接记录包括：镜像版本；电表模板 id 与确认后的字序；批准的安全限值与批准人；已核实写入的命令审计记录；故障注入产生的回滚日志；告警历史。容器日志（`docker logs missionpack_knn`）会轮转覆盖，及时拷出。

#### 下一步

1. 先只在一个区域开启写入，观察满一个周期再扩大范围。
2. 为 critical 级 compensation-failed 告警配置通知。
3. 机组每次再平衡后重新批准安全限值。

## 套餐: SenseCAP 云 {#cloud}

SenseCAP S21xx 节点已通过 SenseCAP M2 网关上报到 SenseCAP 云，射频侧不做改动。桥容器从云端拉取历史与实时数据，发布为本地 Home Assistant 实体。

- **主机：** 一台装 Docker 的 Linux 主机，运行 Home Assistant、MQTT broker 和桥。
- **账号：** SenseCAP Portal 账号和一对 API 密钥。
- **已知限制：** 云 MQTT 有两个候选域名，部署时二选一，首次部署后先看桥的日志确认连接成功。

## 步骤 1: 部署 Home Assistant 与 broker {#deploy_ha type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

在一台主机上启动 Home Assistant 和 Mosquitto broker。已有这两样且桥能连上现有 broker 时可跳过。

### 前置条件

1. 主机至少 8 GB 可用磁盘。
2. 8123 与 1883 端口空闲，或在本步骤的输入里改端口。
3. 设定一个 broker 密码并记下，桥那一步要填同一个值。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 8123 或 1883 已被占用 | 停掉已有的 Home Assistant 或 Mosquitto，或在本步骤的输入里改端口 |
| Mosquitto 反复重启并报 `Unable to open pwfile` | 把密码文件属主改为 `mosquitto` 用户 |
| Home Assistant 一直不响应 8123 | 首次启动需要几分钟，执行 `docker logs agri-env-homeassistant` 查看 |
| 部署连不上 | 确认 SSH 可达、用户名正确（Raspberry Pi OS 用 `pi`，reComputer 用 `recomputer`） |

### 部署目标 {#deploy_ha_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

通过 SSH 部署到一台装 Docker 的 Linux 主机，amd64 或 arm64 均可。

### 部署目标 {#deploy_ha_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

部署到本机，本机须为装 Docker 的 Linux 主机。

---

## 步骤 2: 部署云桥接 {#deploy_cloud_bridge type=docker_deploy required=true config=devices/cloud_bridge.yaml}

部署读取 SenseCAP 云的桥，它会列出账号下的设备、回填历史，然后订阅实时数据。

### 前置条件

1. SenseCAP API 密钥（Access ID 与 Access Key），在 SenseCAP Portal「安全 → Access API Keys」获取。
2. 步骤 1 的 broker 地址、端口、用户名与密码。桥在另一台机器上时，地址填局域网 IP，不要填 `127.0.0.1`。
3. 回填窗口：最多三个月，窗口越长请求越多。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 桥的日志显示云端域名 DNS 失败 | 在 MQTT 域名选择框换另一个域名重新部署 |
| 桥的日志显示认证失败 | 检查 Access ID 与 Access Key 是否配对、密钥是否已在 Portal 吊销 |
| 设备出现了但没有数值 | 回填只写入每个实体的最新值；节点按小时上报时，第一条实时更新最多等一小时 |
| 部署时报 `no such image` | 自建了 `BRIDGE_IMAGE` 时，先在本地构建再重跑 |
| broker 里没有数据 | 桥不在 Home Assistant 主机上时，broker 地址改填局域网 IP |

### 部署目标 {#cloud_bridge_remote type=remote device_name="Bridge Host" config=devices/cloud_bridge.yaml default=true}

通过 SSH 把桥部署到一台装 Docker 的主机。

### 部署目标 {#cloud_bridge_local type=local device_name="Bridge Host" config=devices/cloud_bridge.yaml}

部署到本机，本机须已装 Docker。

---

## 步骤 3: 在 Home Assistant 里核对数据 {#verify_cloud type=web_dashboard required=false config=devices/ha_dashboard.yaml}

打开 Home Assistant，确认节点以设备和实体出现。

### 部署完成

账号下每个节点是一台名为 `SenseCAP <DevEUI>` 的 Home Assistant 设备，每个测量项一个实体。

#### 快速验证

1. 登录 Home Assistant，全新安装时先完成引导向导。
2. 「设置 → 设备与服务 → 添加集成 → **MQTT**」，broker 填运行本套服务的主机、端口 1883、步骤 1 的用户名密码。已配过 MQTT 就跳过。
3. 打开 MQTT 集成，打开一台设备，实体带单位（`°C`、`%`、`dS/m`）。
4. 导入看板：「概览 → 右上角三点 → 编辑仪表板 → 三点 → 原始配置编辑器」，粘贴 `assets/homeassistant/agri_env_dashboard.yaml`，把示例 DevEUI 换成自己的。
5. 导入阈值告警：把 `assets/homeassistant/automations.yaml` 并入 Home Assistant 的 `automations.yaml` 并重载自动化。随包的 `for:` 持续时间为零，现场使用前按需调整阈值与持续时间，避免单次读数抖动误报。

#### 下一步

- 把离线判定时长调成与节点上报间隔匹配。默认按每小时上报设置，每六小时上报的节点会在两次上行之间被标为离线。
- 把需要据以操作的实体单独放一个视图。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| MQTT 集成连上了但没有设备 | 执行 `docker logs agri-env-bridge-cloud`，确认有云端连接成功的日志 |
| 实体一出现就是 `unavailable` | 确认节点在上报，且离线判定时长不短于上报间隔 |
| 某个实体没有单位 | 把它的 `measurementId` 加进 `assets/config/measurements.yaml` |
| 旧的实体 ID 总是回来 | 同时清掉 broker 的 retained 消息和 Home Assistant 的实体注册表 |

---

## 套餐: 自建 The Things Stack {#tts_local}

reComputer R12 系列网关接收 SenseCAP S21xx 节点数据，交给自建的 The Things Stack 开源版，桥订阅它的 MQTT 并发布为 Home Assistant 实体，不需要云账号。

- **主机：** 一台装 Docker 的 Linux 主机，运行 Home Assistant、MQTT broker 和桥。
- **节点：** 每个节点的 DevEUI、JoinEUI 与 AppKey，节点频段与网关一致。
- **已知限制：** 启动 stack 前先确认网关主机可用内存。

## 步骤 1: 部署 Home Assistant 与 broker {#deploy_ha_tts type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

在一台主机上启动 Home Assistant 和 Mosquitto broker。

### 前置条件

1. 主机至少 8 GB 可用磁盘。
2. 8123 与 1883 端口空闲，或在本步骤的输入里改端口。
3. 设定一个 broker 密码并记下，stack 那一步要填同一个值。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 8123 或 1883 已被占用 | 停掉占用端口的进程，或在本步骤的输入里改端口 |
| Mosquitto 反复重启并报 `Unable to open pwfile` | 把密码文件属主改为 `mosquitto` 用户 |
| Home Assistant 一直不响应 8123 | 首次启动需要几分钟，执行 `docker logs agri-env-homeassistant` 查看 |
| 部署连不上 | 检查 SSH 与所用系统镜像的用户名 |

### 部署目标 {#deploy_ha_tts_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

通过 SSH 部署到一台装 Docker 的 Linux 主机。

### 部署目标 {#deploy_ha_tts_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

部署到本机，本机须为装 Docker 的 Linux 主机。

---

## 步骤 2: 启用网关射频 {#r12_gateway_tts type=manual required=true config=devices/r12_gateway_tts.yaml}

在 R12 上接好天线、确认 SPI 设备，并运行指向 The Things Stack 的 packet forwarder。

### 接线

1. 上电前先把 LoRa 天线接到 SMA 座上，未接天线发射可能损坏射频。
2. 确认 `/dev/spidev0.0` 存在，没有就打开 SPI 后重启。
3. 从 R12 产品 wiki 查到 reset、power-enable 与 SX1261 的引脚编号并记下，packet forwarder 配置要用。
4. 核对网关下单时的地区频段与节点频段一致，频段无法在软件里修改。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| forwarder 退出且没打印 EUI | 确认 `/dev/spidev0.0` 存在，再核对 reset 引脚 |
| Console 里网关一直未连接 | 检查防火墙是否放行到 stack 主机的 UDP 1700 |
| 集中器起来了但没有上行 | 核对网关频段、频率计划与节点频段是否一致 |

---

## 步骤 3: 部署 The Things Stack 与桥 {#deploy_tts type=docker_deploy required=true config=devices/tts_stack.yaml}

启动 The Things Stack（含 Postgres 与 Redis）并初始化，同时启动桥。首次运行预留 15–30 分钟。

### 前置条件

1. 至少 10 GB 可用磁盘。
2. 主机的局域网 IP（不要填 `127.0.0.1`，否则其他机器无法登录 Console）。
3. 1885（Console）与 1700/udp（packet forwarder）端口空闲。
4. 步骤 1 的 broker 地址、端口、用户名与密码。
5. application ID 与 API key 在步骤 4 创建：先部署本步骤，在 Console 创建后填入，再执行 `docker compose restart bridge`。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| `is-db migrate` 失败 | Postgres 未就绪，重跑初始化 |
| Console 打得开但登录反复跳转 | 用主机局域网 IP 重新部署 |
| 桥的日志里没有 `TTS MQTT connected` | 在步骤 4 创建 application 和 API key 后重启桥 |
| stack 容器一起来就被杀 | 检查主机可用内存 |

### 部署目标 {#tts_stack_remote type=remote device_name="Gateway Host" config=devices/tts_stack.yaml default=true}

通过 SSH 部署到网关主机。

### 部署目标 {#tts_stack_local type=local device_name="Gateway Host" config=devices/tts_stack.yaml}

部署到本机，本机须为网关主机。

---

## 步骤 4: 让传感器接入 The Things Stack {#join_tts type=manual required=true config=devices/join_tts_device.yaml}

创建 application、安装 payload formatter、让节点入网。

### 前置条件

1. 网关在 Console 里显示为 `Connected`。
2. 每个节点的 DevEUI、JoinEUI 与 AppKey，印在节点上，也可用 SenseCAP Mate app 通过 NFC 读出。
3. 节点系列对应的 SenseCAP decoder（上游仓库），没有它实体不会出现。该仓库没有 LICENSE 文件，许可状态未确认。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 有 join request 但没有 join accept | 核对密钥和区域参数 |
| 连 join request 都没有 | 先看网关状态，确认网关收到节点信号 |
| 上行到了但没有 `decoded_payload` | 在该 application 上安装 payload formatter |
| 有 `decoded_payload` 但没有 `messages` 数组 | 换成与节点系列对应的 decoder |

---

## 步骤 5: 在 Home Assistant 里核对数据 {#verify_tts type=web_dashboard required=false config=devices/ha_dashboard.yaml}

打开 Home Assistant，确认节点已经出现。

### 部署完成

每个入网节点在 Home Assistant 里是一台设备，实体 ID 与其他套餐一致。

#### 快速验证

1. 登录 Home Assistant，全新安装时先完成引导向导。
2. 「设置 → 设备与服务 → 添加集成 → **MQTT**」，指向步骤 1 的 broker。
3. 打开 MQTT 集成，每个节点是一台名为 `SenseCAP <DevEUI>` 的设备，打开一台确认实体带单位。
4. 把 `assets/homeassistant/agri_env_dashboard.yaml` 粘进 Lovelace 原始配置编辑器，把示例 DevEUI 换成自己的。
5. 把 `assets/homeassistant/automations.yaml` 并入 Home Assistant 的 `automations.yaml`，重载自动化，按现场设置阈值与 `for:` 持续时间。

#### 下一步

- 把离线判定时长调成与节点上报间隔匹配。
- 第一天保持 Console 的网关页面打开，网关掉线重连会先在那里显示。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 设备出现了但实体是 `unavailable` | 核对上报间隔与离线判定时长 |
| 只有一个节点缺失 | 看该节点在 Console 里的 Live data，有上行时检查 decoder |
| 某个实体没有单位 | 把它的 `measurementId` 加进 `assets/config/measurements.yaml` |
| 旧的实体 ID 总是回来 | 同时清掉 broker 的 retained 消息和实体注册表 |

---

## 套餐: 本地 ChirpStack {#chirpstack_local}

ChirpStack 作网络服务器，用 SenseCAP M2 网关内置的 ChirpStack，或在 reComputer R12 系列网关上用 Docker 运行，SenseCAP S21xx 节点数据全程不经外网。

- **主机：** 一台装 Docker 的 Linux 主机，运行 Home Assistant、MQTT broker 和桥。
- **节点：** 每个节点的 DevEUI、JoinEUI 与 AppKey，节点频段与网关一致。
- **已知限制：** M2 切到本地模式后脱离 SenseCAP 云，固件能否同时上报云端和本地须在实机上确认。

## 步骤 1: 部署 Home Assistant 与 broker {#deploy_ha_cs type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

在一台主机上启动 Home Assistant 和 Mosquitto broker。

### 前置条件

1. 主机至少 8 GB 可用磁盘。
2. 8123 与 1883 端口空闲，或在本步骤的输入里改端口。
3. 设定一个 broker 密码并记下，ChirpStack 那一步要填同一个值。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 8123 或 1883 已被占用 | 停掉占用端口的进程，或在本步骤的输入里改端口 |
| Mosquitto 反复重启并报 `Unable to open pwfile` | 把密码文件属主改为 `mosquitto` 用户 |
| Home Assistant 一直不响应 8123 | 首次启动需要几分钟，执行 `docker logs agri-env-homeassistant` 查看 |
| 部署连不上 | 检查 SSH 与所用系统镜像的用户名 |

### 部署目标 {#deploy_ha_cs_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

通过 SSH 部署到一台装 Docker 的 Linux 主机。

### 部署目标 {#deploy_ha_cs_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

部署到本机，本机须为装 Docker 的 Linux 主机。

---

## 步骤 2: 把 M2 切到本地网络服务器 {#m2_local_lns type=manual required=false config=devices/m2_local_lns.yaml}

让 M2 脱离云端并打开内置的 ChirpStack。本步骤与步骤 3 **二选一**。

### 前置条件

1. M2 的局域网 IP 与 Web 界面凭据。
2. 在状态页记下型号、频段与固件版本；菜单路径为 `LoRa → LoRa Network`，与此不同时先核对固件版本。
3. 内置网络服务器要发布到的 MQTT 地址、端口、用户名与密码，桥会订阅这个 broker。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| Portal 里不再出现上行 | 本地模式下属正常 |
| 内置 ChirpStack 里没有 application | 在步骤 5 入网前先建好 tenant、application 与 device profile |
| 上行到了但没有 `object` | 把节点系列对应的 SenseCAP decoder 粘进 device profile 的 codec |

---

## 步骤 3: 启用网关射频 {#r12_gateway_chirpstack type=manual required=false config=devices/r12_gateway_chirpstack.yaml}

与步骤 2 二选一：用 reComputer R12 系列网关代替 M2，网关与 ChirpStack 都运行在 R12 上。

### 接线

1. 上电前先把 LoRa 天线接到 SMA 座上。
2. 确认 `/dev/spidev0.0` 存在，没有就打开 SPI 后重启。
3. 从 R12 产品 wiki 查到 reset、power-enable 与 SX1261 的引脚编号并记下。
4. 网关下单时的地区频段须与步骤 4 选的频率计划、节点频段一致。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| forwarder 退出且没打印 EUI | 确认 SPI 已打开，再核对 reset 引脚 |
| 网关的 `Last seen` 一直不更新 | 检查防火墙是否放行 UDP 1700 |
| concentratord 起来了但 gateway bridge 收不到数据 | 先改用 UDP packet forwarder 跑通上行，再排查容器内能否访问 concentratord 的 ZMQ 端点 |

---

## 步骤 4: 部署 ChirpStack 与桥 {#deploy_chirpstack type=docker_deploy required=true config=devices/chirpstack_stack.yaml}

选 `m2` 只启动桥；选 `local` 则在本机同时启动 ChirpStack。

### 前置条件

1. `m2` 路线：步骤 2 里 M2 的 broker 地址、端口、用户名与密码。
2. `local` 路线：至少 8 GB 可用磁盘，频率计划与网关和节点一致。
3. 步骤 1 的 broker 地址、端口、用户名与密码。
4. application ID，填 `+` 订阅该 broker 上的所有 application。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 桥的日志里没有 `ChirpStack MQTT connected` | `m2` 路线核对网关 LoRa Network 页面上的地址与凭据；`local` 路线执行 `docker compose --profile local-lns ps` |
| `local` 路线上 ChirpStack 服务没起来 | 确认 `lns_mode` 选的是 `local` 后重跑本步骤 |
| 8080 上的 Web 界面访问不到 | 只有 `local` 路线有该界面，`m2` 路线在网关的 Web 界面操作 |
| 部署时报 `no such image` | 自建了 `BRIDGE_IMAGE` 时，先在本地构建再重跑 |

### 部署目标 {#chirpstack_remote type=remote device_name="Bridge Host" config=devices/chirpstack_stack.yaml default=true}

通过 SSH 部署到运行桥的主机。

### 部署目标 {#chirpstack_local_target type=local device_name="Bridge Host" config=devices/chirpstack_stack.yaml}

部署到本机，本机即运行桥的主机。

---

## 步骤 5: 让传感器接入 ChirpStack {#join_chirpstack type=manual required=true config=devices/join_chirpstack_device.yaml}

注册节点并确认上行能解码。

### 前置条件

1. 一个 LoRaWAN 版本与区域参数都匹配节点的 device profile，codec 里填该系列的 SenseCAP decoder（上游仓库没有 LICENSE 文件，许可状态未确认）。
2. 每个节点的 DevEUI、JoinEUI 与 AppKey。
3. 网关在 ChirpStack 里可见，`Last seen` 为近期。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| ChirpStack 拒绝这个 DevEUI | 该 DevEUI 已存在于另一个 tenant，从其他网络迁移节点时常见 |
| 有 join request 但没有 accept | 核对密钥和区域参数 |
| 上行里没有 `object.messages` | 给 device profile 配上与节点系列对应的 codec |

---

## 步骤 6: 在 Home Assistant 里核对数据 {#verify_chirpstack type=web_dashboard required=false config=devices/ha_dashboard.yaml}

打开 Home Assistant 确认节点已出现；无公网部署还要确认断网后照常工作。

### 部署完成

从节点到看板的数据都在本地网络内，不依赖云账号。

#### 快速验证

1. 登录 Home Assistant，全新安装时先完成引导向导。
2. 「设置 → 设备与服务 → 添加集成 → **MQTT**」，指向步骤 1 的 broker。
3. 打开 MQTT 集成，每个节点是一台名为 `SenseCAP <DevEUI>` 的设备，打开一台确认实体带单位。
4. 把 `assets/homeassistant/agri_env_dashboard.yaml` 粘进 Lovelace 原始配置编辑器，把示例 DevEUI 换成自己的。
5. 把 `assets/homeassistant/automations.yaml` 并入 Home Assistant 的 `automations.yaml`，重载自动化，按现场设置阈值与 `for:` 持续时间。

#### 无公网验收

看板跑通后做一次：

1. 记下每个节点一个实体的当前值与最后更新时间。
2. 断开场地 WAN（拔掉上行链路或在防火墙拦截出站流量），局域网保持连通。
3. 等至少两个上报周期，每个实体都应继续更新；有停更的，查看桥的日志和网关页面。
4. 重启网关，记录从上电到第一条上行出现在 Home Assistant 的时间，作为该场地的恢复时间。
5. 恢复 WAN，数据不受影响。

#### 下一步

- 把离线判定时长调成与节点上报间隔匹配。
- 物理隔离的场地，趁主机还能联网先拉取容器镜像，或从归档 load，断网后无法拉取。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 设备出现了但实体是 `unavailable` | 核对上报间隔与离线判定时长 |
| 一断 WAN 实体就停更 | 查看桥的日志和网关的网络页面，找出仍访问外网的环节 |
| 某个实体没有单位 | 把它的 `measurementId` 加进 `assets/config/measurements.yaml` |
| 旧的实体 ID 总是回来 | 同时清掉 broker 的 retained 消息和实体注册表 |

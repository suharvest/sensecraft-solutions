## 套餐: SenseCAP 云 {#cloud}

节点已经通过你现有的网关向 SenseCAP 云上报。射频侧不做任何改动。
一个桥容器读云端——先拉历史，再订阅实时流——并把 Home Assistant 实体发布到本地 broker。

| 设备 | 作用 |
|--------|---------|
| SenseCAP S21xx 节点 | 测土壤与空气，通过 LoRaWAN 上报 |
| SenseCAP M2 网关 | 把上行转发到 SenseCAP 云 |
| 装 Docker 的 Linux 主机 | 运行 Home Assistant、MQTT broker 和桥 |

**重要：** 本套餐没有在真实 SenseCAP 账号上跑过。
云 MQTT 域名未经确认——目前有两个候选，部署步骤里两个都提供。
OpenAPI 回填也从未在真实响应上验证过。
把第一次部署当成 bring-up，先读桥的日志，再去信看板。

## 步骤 1: 部署 Home Assistant 与 broker {#deploy_ha type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

在一台主机上起 Home Assistant 和 Mosquitto broker。
只有在你已经跑着这两样、并且能让桥连上现有 broker 时才跳过。

### 前置条件

1. 一台 Docker 在跑、SSH 可达的 Linux 主机。任何架构都行——这里用到的镜像 amd64 和 arm64 都有。
2. 至少 8 GB 空闲磁盘。仅 Home Assistant 镜像就约 1.5 GB。
3. 8123 与 1883 端口空闲，或在本步骤的输入里改成别的端口。
4. 现在定一个 broker 密码。桥那一步要填同一个值，记下来——
   broker 刻意不接受匿名连接，因为桥可能跑在另一台机器上。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 8123 或 1883 已被占用 | 有别的东西在用——通常是已有的 Home Assistant 或 Mosquitto。停掉它，或在本步骤的输入里改端口 |
| Mosquitto 反复重启并报 `Unable to open pwfile` | 密码文件写出来了但属主不是 `mosquitto` 用户。随包的 compose 文件用 `chown` 处理了这一点；手改的副本漏掉它就会这样失败 |
| Home Assistant 一直不响应 8123 | 首启要几分钟。先看 `docker logs agri-env-homeassistant`，再下失败的结论 |
| 部署连不上 | 确认 SSH 可达、用户名正确——Raspberry Pi OS 用 `pi`，Seeed reComputer 镜像用 `recomputer` |

### 部署目标 {#deploy_ha_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

从这台电脑通过 SSH 部署到目标主机。

### 部署目标 {#deploy_ha_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

如果你就在那台机器上操作，直接本地运行。

---

## 步骤 2: 部署云桥接 {#deploy_cloud_bridge type=docker_deploy required=true config=devices/cloud_bridge.yaml}

部署启用了 SenseCAP 云 source 的桥。它会列出账号下的设备，回填历史，然后订阅实时流。

### 前置条件

1. 一对 SenseCAP API 密钥——Access ID 与 Access Key——在 SenseCAP Portal 的
   「安全 → Access API Keys」里获取。Access Key 只写入目标主机上权限 600 的 `.env` 文件。
2. 步骤 1 的 broker 地址、端口、用户名与密码。桥在另一台机器上时，填局域网地址而不是 `127.0.0.1`。
3. 桥的镜像。`agri-env-bridge:0.1.0` **尚未发布到任何 registry**——
   部署前先从上游项目构建，或把 `BRIDGE_IMAGE` 指向你自己托管的 tag。
4. 定好回填窗口。OpenAPI 最多回溯三个月、单次一个月，所以选三个月意味着每台设备三倍的请求量。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 桥的日志显示云端域名 DNS 失败 | 两个候选域名都未经确认。用 MQTT 域名选择框里的另一个重新部署 |
| 桥的日志显示认证失败 | 检查 Access ID 与 Access Key 是否配对，以及该密钥是否已在 Portal 里被吊销 |
| 设备出现了但没有数值 | 回填只把每个实体的最新值送进 Home Assistant。节点如果按小时上报，第一条实时更新可能要等一小时 |
| 部署时报 `no such image` | 镜像 tag 未发布。先本地构建再重跑 |
| 什么都没进 broker | 桥不在 Home Assistant 主机上时，broker 地址要填局域网地址，不能是 `127.0.0.1` |

### 部署目标 {#cloud_bridge_remote type=remote device_name="Bridge Host" config=devices/cloud_bridge.yaml default=true}

通过 SSH 把桥部署到目标主机。

### 部署目标 {#cloud_bridge_local type=local device_name="Bridge Host" config=devices/cloud_bridge.yaml}

直接在那台主机上运行。

---

## 步骤 3: 在 Home Assistant 里核对数据 {#verify_cloud type=web_dashboard required=false config=devices/ha_dashboard.yaml}

打开 Home Assistant，确认节点已经作为设备连同实体出现。

### 部署完成

账号下的每个节点现在都是一台名为 `SenseCAP <DevEUI>` 的 Home Assistant 设备，
它上报的每个测量项对应一个实体。

#### 快速验证

1. 登录 Home Assistant；如果是全新安装，先走完引导向导。
2. 「设置 → 设备与服务 → 添加集成 → **MQTT**」。Broker 填运行本套栈的主机，端口 1883，
   用户名密码用步骤 1 里设的那组。已经配过 MQTT 就跳过。
3. 打开 MQTT 集成。每个节点是一台设备；打开一台，确认它的实体带单位——
   `°C`、`%`、`dS/m`——而不是光秃秃的数字。
4. 导入看板：「概览 → 右上角三点 → 编辑仪表板 → 三点 → 原始配置编辑器」，
   粘贴 `assets/homeassistant/agri_env_dashboard.yaml`，再把示例 DevEUI 换成你自己的。
5. 装阈值告警：把 `assets/homeassistant/automations.yaml` 并入 Home Assistant 的
   `automations.yaml` 并重载自动化。阈值和 `for:` 持续时间要自己调——
   随包的持续时间是零，这对测试合适，对现场不合适，单次读数抖动就会误报。

#### 下一步

- 把离线判定时长调成与节点上报间隔匹配。默认按小时上报设的；
  每六小时上报一次的节点会在两次上行之间被标成离线。
- 把你真正要据以行动的实体单独放一个视图。
  把每个节点的每个测量项都列出来的看板，没有人会看。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| MQTT 集成连上了但没有设备 | 桥没在发。看 `docker logs agri-env-bridge-cloud` 里有没有云端连接那一行 |
| 实体一出现就是 `unavailable` | 离线判定时长内没有上行。要么节点没在报，要么阈值比上报间隔还短 |
| 某个实体没有单位 | 它的 `measurementId` 不在 `assets/config/measurements.yaml` 里。加进去——该文件为每条已有记录都标了 decoder 源码行号 |
| 旧的实体 ID 总是回来 | 自动发现配置是 retained 的。要同时清掉 broker 的 retained 消息和 Home Assistant 的实体注册表，否则重启后旧主题还会出现 |

---

## 套餐: 自建 The Things Stack {#tts_local}

网络服务器由你自己跑。CM4 主机上的 WM1302 集中器把数据喂给一个 The Things Stack
开源版实例，桥订阅它的 Application Server MQTT。不涉及任何云账号。

| 设备 | 作用 |
|--------|---------|
| SenseCAP S21xx 节点 | 测土壤与空气，通过 LoRaWAN 上报 |
| WM1302 集中器 | 网关的射频部分，走 SPI |
| CM4 主机 | 承载集中器，运行 packet forwarder 和 stack |
| 装 Docker 的 Linux 主机 | 运行 Home Assistant、MQTT broker 和桥 |

**重要：** 本套餐没有任何一部分在硬件上跑过。集中器没装过，
stack 没在 ARM64 目标上起过，它的首启初始化流程也没执行过，资源下限未测。
下面标着待验证的步骤都是照模块与 stack 文档写的，
而且每一条都属于"会以板卡特有方式失败"的那类步骤。

## 步骤 1: 部署 Home Assistant 与 broker {#deploy_ha_tts type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

与其它套餐相同的 Home Assistant 与 broker。先部署它，桥才有地方发数据。

### 前置条件

1. 一台 Docker 在跑、SSH 可达的 Linux 主机。
2. 至少 8 GB 空闲磁盘。
3. 8123 与 1883 端口空闲，或在本步骤的输入里改端口。
4. 现在定一个 broker 密码——stack 那一步要填同一个值。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 8123 或 1883 已被占用 | 停掉占用它的进程，或在本步骤的输入里改端口 |
| Mosquitto 反复重启并报 `Unable to open pwfile` | 密码文件属主必须是 `mosquitto` 用户；随包的 compose 文件已处理 |
| Home Assistant 一直不响应 8123 | 首启要几分钟——先读 `docker logs agri-env-homeassistant` |
| 部署连不上 | 检查 SSH 与你所用镜像的用户名 |

### 部署目标 {#deploy_ha_tts_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

通过 SSH 部署到目标主机。

### 部署目标 {#deploy_ha_tts_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

直接在那台主机上运行。

---

## 步骤 2: 安装 WM1302 集中器 {#wm1302_tts type=manual required=true config=devices/wm1302_tts.yaml}

装模块、打开 SPI、跑一个指向 stack 的 packet forwarder。
**待真机验证**——打包过程中没有装过 WM1302。

### 接线

1. 装模块前先断电。上电之前先接好 LoRa 天线；开路发射可能损坏射频。
2. 用 SPI 版模块，主机上打开 SPI 后确认 `/dev/spidev0.0` 出现。
3. reset、power-enable 与 SX1261 三条控制线来自载板文档，不是模块文档。
   把引脚编号记下来——packet forwarder 的配置要用。
4. 核对模块上印的频段与节点所用频段。不一致的表现就是网关什么都收不到。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| forwarder 退出且没打印 EUI | SPI 没打开，或 reset 线接错。先确认 `/dev/spidev0.0` 存在 |
| Console 里网关一直未连接 | UDP 1700 没通到 stack 主机。先查防火墙，再动射频配置 |
| 集中器起来了但没有上行 | 模块频段、频率计划与节点频段三者不一致，是首先要排除的 |

---

## 步骤 3: 部署 The Things Stack 与桥 {#deploy_tts type=docker_deploy required=true config=devices/tts_stack.yaml}

拉起带 Postgres 与 Redis 的 The Things Stack，做初始化，并在旁边启动桥。
首轮预留 15–30 分钟。

### 前置条件

1. 至少 10 GB 空闲磁盘，用于 stack、数据库、Redis 三个镜像以及数据库卷。
2. 主机的局域网地址。Console 的 OAuth 地址是用它拼出来的，
   填 `127.0.0.1` 会导致别的机器登不进 Console。
3. 1885（Console）与 1700/udp（packet forwarder）端口空闲。
4. 步骤 1 的 broker 地址、端口、用户名与密码。
5. 桥的镜像。`agri-env-bridge:0.1.0` **尚未发布到任何 registry**——
   自行构建或覆盖 `BRIDGE_IMAGE`。
6. application ID 与 API key 在这一步要填，但要到步骤 4 才创建。
   先部署本步骤，在 Console 里创建它们，再用
   `docker compose restart bridge` 重启桥。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `is-db migrate` 失败 | Postgres 还没就绪。重跑初始化——里面每条命令都可以安全重复执行 |
| Console 打得开但登录反复跳转 | OAuth 地址是用错的 host 拼的。改用局域网地址重新部署 |
| 桥的日志里没有 `TTS MQTT connected` | application 或它的 API key 还不存在。到步骤 4 建好再重启桥 |
| stack 容器一起来就被杀 | 资源下限未测——先看可用内存，再怀疑配置写错 |

### 部署目标 {#tts_stack_remote type=remote device_name="Gateway Host" config=devices/tts_stack.yaml default=true}

通过 SSH 部署到网关主机。

### 部署目标 {#tts_stack_local type=local device_name="Gateway Host" config=devices/tts_stack.yaml}

直接在网关主机上运行。

---

## 步骤 4: 让传感器接入 The Things Stack {#join_tts type=manual required=true config=devices/join_tts_device.yaml}

创建 application、安装 payload formatter、让节点入网。
**待真机验证**——打包过程中没有节点入过网。

### 前置条件

1. 网关在 Console 里显示为 `Connected`。
2. 每个节点的 DevEUI、JoinEUI 与 AppKey，印在节点上，也可用 SenseCAP Mate app 通过 NFC 读出。
3. 你的节点系列对应的 SenseCAP decoder，从上游仓库取。上行是二进制的——
   没有它一个实体也出不来。该仓库没有 LICENSE 文件、许可状态未确认，是否安装请自行判断。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 有 join request 但没有 join accept | 密钥或区域参数与节点不匹配 |
| 连 join request 都没有 | 网关根本没听到节点。先看网关状态，再回头查密钥 |
| 上行到了但没有 `decoded_payload` | payload formatter 没装，或挂在了别的 application 上 |
| 有 `decoded_payload` 但没有 `messages` 数组 | decoder 与节点系列对不上——要取你这一系列的，不是相邻那个 |

---

## 步骤 5: 在 Home Assistant 里核对数据 {#verify_tts type=web_dashboard required=false config=devices/ha_dashboard.yaml}

打开 Home Assistant，确认节点已经出现。

### 部署完成

节点跑在你自己掌控的网络服务器上，它们的测量项在 Home Assistant 里是实体，
实体 ID 与其它套餐产出的完全一致。

#### 快速验证

1. 登录 Home Assistant；如果是全新安装，先走完引导向导。
2. 「设置 → 设备与服务 → 添加集成 → **MQTT**」，指向步骤 1 的 broker。
3. 打开 MQTT 集成。每个入网的节点是一台名为 `SenseCAP <DevEUI>` 的设备；
   打开一台，确认单位都在。
4. 把 `assets/homeassistant/agri_env_dashboard.yaml` 粘进 Lovelace 原始配置编辑器，
   再把示例 DevEUI 换成你自己的。
5. 把 `assets/homeassistant/automations.yaml` 并入 Home Assistant 的 `automations.yaml`，
   重载自动化，并按你的现场设置阈值与 `for:` 持续时间。

#### 下一步

- 把离线判定时长调成与节点上报间隔匹配。
- 头一天把 Console 的网关页面开着。网关掉线重连在那里显示的时间，远早于看板上反映出来的时间。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 设备出现了但实体是 `unavailable` | 离线判定时长内没有上行——对一下上报间隔与阈值 |
| 别的节点正常，只有一个缺失 | 看那个节点在 Console 里的 Live data。如果那里有上行，差别就在 decoder |
| 某个实体没有单位 | 它的 `measurementId` 不在 `assets/config/measurements.yaml` 里，加进去 |
| 旧的实体 ID 总是回来 | retained 的自动发现配置。要同时清 broker 的 retained 消息和实体注册表 |

---

## 套餐: 本地 ChirpStack {#chirpstack_local}

ChirpStack 作网络服务器，可以是 M2 网关内置的，也可以是跑在装了 WM1302 的 CM4 主机上的
Docker 版本。这是走到"全程不碰外网"部署的最短路径。

| 设备 | 作用 |
|--------|---------|
| SenseCAP S21xx 节点 | 测土壤与空气，通过 LoRaWAN 上报 |
| SenseCAP M2 网关 | 射频；切到本地模式后它本身就是网络服务器 |
| CM4 主机 + WM1302 | M2 之外的另一条路——用 Docker 跑 ChirpStack |
| 装 Docker 的 Linux 主机 | 运行 Home Assistant、MQTT broker 和桥 |

**重要：** 本套餐的两条路线都没有在硬件上跑过。没有 M2 被切到本地模式，
没有装过集中器，ChirpStack 也没在 ARM64 目标上起过。
M2 能否同时向云端和本地网络服务器上报，尚未核实——
在你手上那台机器上确认之前，不要按这个假设做规划。

## 步骤 1: 部署 Home Assistant 与 broker {#deploy_ha_cs type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

与其它套餐相同的 Home Assistant 与 broker。

### 前置条件

1. 一台 Docker 在跑、SSH 可达的 Linux 主机。
2. 至少 8 GB 空闲磁盘。
3. 8123 与 1883 端口空闲，或在本步骤的输入里改端口。
4. 现在定一个 broker 密码——ChirpStack 那一步要填同一个值。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 8123 或 1883 已被占用 | 停掉占用它的进程，或在本步骤的输入里改端口 |
| Mosquitto 反复重启并报 `Unable to open pwfile` | 密码文件属主必须是 `mosquitto` 用户；随包的 compose 文件已处理 |
| Home Assistant 一直不响应 8123 | 首启要几分钟——先读 `docker logs agri-env-homeassistant` |
| 部署连不上 | 检查 SSH 与你所用镜像的用户名 |

### 部署目标 {#deploy_ha_cs_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

通过 SSH 部署到目标主机。

### 部署目标 {#deploy_ha_cs_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

直接在那台主机上运行。

---

## 步骤 2: 把 M2 切到本地网络服务器 {#m2_local_lns type=manual required=false config=devices/m2_local_lns.yaml}

把网关从云端摘下来，打开它内置的 ChirpStack。本步骤与步骤 3 **二选一**，不要都做。
**待真机验证**——打包过程中没有切换过 M2。

### 前置条件

1. M2 的局域网地址与 Web 界面凭据。
2. 状态页上的型号、频段与固件版本，记下来。下面用到的菜单路径是
   `LoRa → LoRa Network`；如果你看到的不一样，提问时首先要说清的就是固件版本。
3. 供内置网络服务器发布用的 MQTT 地址、端口、用户名与密码。这是直连 MQTT——
   不是 Semtech UDP，也不是 Basic Station——所以桥订阅的是那个 broker。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| Portal 里不再出现上行 | 属预期——本地模式会把网关从云端摘下来。这一版固件能否两者并行，尚未核实 |
| 内置 ChirpStack 里没有 application | 在步骤 5 让节点入网之前，先建好 tenant、application 与 device profile |
| 上行到了但没有 `object` | device profile 没配 codec。把你节点系列对应的 SenseCAP decoder 粘进去 |

---

## 步骤 3: 安装 WM1302 集中器 {#wm1302_chirpstack type=manual required=false config=devices/wm1302_chirpstack.yaml}

步骤 2 之外的另一条路：在 CM4 主机上自己搭网关，并在那里跑 ChirpStack。
**待真机验证**——打包过程中没有装过 WM1302。

### 接线

1. 装模块前先断电，上电之前先接好 LoRa 天线。
2. 用 SPI 版，打开 SPI 后确认 `/dev/spidev0.0` 出现。
3. reset、power-enable 与 SX1261 的引脚编号取自载板文档，记下来。
4. 模块上印的频段必须与步骤 4 选的频率计划、以及节点所用频段一致。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| forwarder 退出且没打印 EUI | SPI 没打开，或 reset 线接错 |
| 网关的 `Last seen` 一直不更新 | 数据包没到——先查防火墙上的 UDP 1700 |
| concentratord 起来了但 gateway bridge 什么都收不到 | 它的 ZMQ 端点必须能从容器内访问。这正是本路线未经验证的部分——先退回 UDP packet forwarder 把上行跑通，再回头处理 |

---

## 步骤 4: 部署 ChirpStack 与桥 {#deploy_chirpstack type=docker_deploy required=true config=devices/chirpstack_stack.yaml}

一个步骤覆盖两条路线。选 `m2` 只起桥；选 `local` 则在本机一并拉起 ChirpStack。

### 前置条件

1. `m2` 路线：步骤 2 里 M2 的 broker 地址、端口、用户名与密码。
2. `local` 路线：至少 8 GB 空闲磁盘，以及与集中器和节点一致的频率计划。
3. 步骤 1 的 broker 地址、端口、用户名与密码。
4. 桥的镜像。`agri-env-bridge:0.1.0` **尚未发布到任何 registry**——
   自行构建或覆盖 `BRIDGE_IMAGE`。
5. application ID。填 `+` 表示订阅该 broker 上的所有 application，
   单租户场地这样最省事。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 桥的日志里没有 `ChirpStack MQTT connected` | `m2` 路线上重新核对网关 LoRa Network 页面上的地址与凭据；`local` 路线上查 `docker compose --profile local-lns ps` |
| `local` 路线上 ChirpStack 服务没起来 | 只有 `lns_mode` 为 `local` 时才会激活那个 profile。选对之后重跑本步骤 |
| 8080 上的 Web 界面访问不到 | 只有 `local` 路线才会起 Web 界面。`m2` 路线上 ChirpStack 在网关里面 |
| 部署时报 `no such image` | 桥的镜像 tag 未发布。先本地构建再重跑 |

### 部署目标 {#chirpstack_remote type=remote device_name="Bridge Host" config=devices/chirpstack_stack.yaml default=true}

通过 SSH 部署到将要运行桥的那台主机。

### 部署目标 {#chirpstack_local_target type=local device_name="Bridge Host" config=devices/chirpstack_stack.yaml}

直接在那台主机上运行。

---

## 步骤 5: 让传感器接入 ChirpStack {#join_chirpstack type=manual required=true config=devices/join_chirpstack_device.yaml}

注册节点并确认上行能解出来。**待真机验证**——打包过程中没有节点入过网。

### 前置条件

1. 一个 LoRaWAN 版本与区域参数都匹配节点的 device profile，
   并且 codec 字段里是该系列对应的 SenseCAP decoder。
   该仓库没有 LICENSE 文件、许可状态未确认，是否安装请自行判断。
2. 每个节点的 DevEUI、JoinEUI 与 AppKey。
3. 网关在 ChirpStack 里可见，且 `Last seen` 是近期的。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| ChirpStack 拒绝这个 DevEUI | 它已经存在于另一个 tenant——把节点从别的网络迁过来时最常撞到 |
| 有 join request 但没有 accept | 密钥或区域参数不匹配 |
| 上行里没有 `object.messages` | device profile 没配 codec，或配的不是这一系列的 |

---

## 步骤 6: 在 Home Assistant 里核对数据 {#verify_chirpstack type=web_dashboard required=false config=devices/ha_dashboard.yaml}

打开 Home Assistant 确认节点已经出现——如果这是一套无公网部署，
接着确认它在断网后照常工作。

### 部署完成

从节点到看板的整条路径都在你自己的网络里。其中没有任何一环依赖云账号。

#### 快速验证

1. 登录 Home Assistant；如果是全新安装，先走完引导向导。
2. 「设置 → 设备与服务 → 添加集成 → **MQTT**」，指向步骤 1 的 broker。
3. 打开 MQTT 集成。每个入网的节点是一台名为 `SenseCAP <DevEUI>` 的设备；
   打开一台，确认单位都在。
4. 把 `assets/homeassistant/agri_env_dashboard.yaml` 粘进 Lovelace 原始配置编辑器，
   再把示例 DevEUI 换成你自己的。
5. 把 `assets/homeassistant/automations.yaml` 并入 Home Assistant 的 `automations.yaml`，
   重载自动化，并按你的现场设置阈值与 `for:` 持续时间。

#### 无公网验收

看板跑通之后做一次，确认这套部署在没有外网时仍然成立：

1. 记下每个节点各一个实体的当前值与最后更新时间。
2. 断掉场地的 WAN——拔掉上行链路，或在防火墙上拦截出站流量。局域网保持通。
3. 等至少两个上报周期。每个实体都必须继续更新。
   如果有停更的，说明路径里还有东西在往外走；桥的日志和网关自己的页面会指出是哪一处。
4. 重启网关。计时从上电到第一条上行出现在 Home Assistant 里花了多久，并记录下来——
   这就是可以对外说的恢复时间数字，而且它因场地而异。
5. 恢复 WAN。什么都不应该变化，因为本来就没有东西在用它。

把测到的数字记下来。本方案不附任何通信距离、节点数或成功率数字，因为都没有测过；
你在这里测出来的，才是描述你这个场地的数字。

#### 下一步

- 把离线判定时长调成与节点上报间隔匹配。
- 物理隔离的场地，趁主机还有网时先把容器镜像拉一次，或从归档里 load——
  compose 文件引用的是公共 registry，断了 WAN 就拉不动。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 设备出现了但实体是 `unavailable` | 离线判定时长内没有上行——对一下上报间隔与阈值 |
| 一断 WAN 实体就停更 | 路径里还有东西在解析或访问外网。读桥的日志和网关的网络页面 |
| 某个实体没有单位 | 它的 `measurementId` 不在 `assets/config/measurements.yaml` 里，加进去 |
| 旧的实体 ID 总是回来 | retained 的自动发现配置。要同时清 broker 的 retained 消息和实体注册表 |

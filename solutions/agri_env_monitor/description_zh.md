# 农业环境监测

## 它做什么

SenseCAP LoRaWAN 节点测土壤和空气——温度、湿度、土壤水分、电导率、CO2、雨量——
通过 LoRaWAN 上报。本方案把这些上行（不管走哪条路进来）变成 Home Assistant 实体，
带上正确的单位、device class 和 state class，于是它们出现在看板上、积累历史，
并能在数值越界时触发通知。

进来的路有三条，终点是同一个。套餐 1 读 SenseCAP 云。套餐 2 读你自建的
The Things Stack。套餐 3 读 ChirpStack——可以是 M2 网关内置的那个，
也可以是你用 Docker 跑在 WM1302 集中器旁边的那个。三条路背后是同一个服务
`agri-env-bridge`：把 SenseCAP 的 `measurementId` 映射成实体语义，去重，
跟踪每个节点是否还在上报，并发布 Home Assistant MQTT 自动发现消息。

## 你会得到什么

**三条路径共用一套实体命名。** 不论由哪个套餐产生，实体都是
`sensor.sensecap_<deveui>_<entity_key>`。一个站点从云端切到本地网络服务器，
不用改看板、不用改自动化、不用改导出。

**有意义的 availability。** 每个节点一个 retained availability 主题。
节点静默超过设定时长就翻成 `offline`，它的实体在 Home Assistant 里显示为不可用——
最后一个值保留，不是清空。默认阈值是 S210x 两个上报周期加余量。

**云套餐首启时回填历史。** 桥按月分页调 SenseCAP OpenAPI，把取到的数据写进本地 SQLite，
主键是 `(DevEUI, measurementId, 时间戳)`，所以回填和实时流不会把同一条读数记两遍。
Home Assistant 收到的是每个实体的最新值；它自己的 recorder 历史从上线那一刻开始积累。

**可直接导入的看板与阈值告警。** 一份 Lovelace 看板，覆盖空气温湿度、土壤温度、
水分与电导率、雨量、电量与可用性；另有一组自动化，数值越界时创建持久通知，
恢复后自动关闭。

**一个完全不联外网的选项。** ChirpStack 跑在网关自己身上，桥和 Home Assistant 跑在本地主机上，
数据不需要离开场地——不用云账号，不用出站连接。

## 适用场景

- 大棚，土壤水分和电导率决定什么时候灌溉、什么时候追肥。
- 大田地块，一个网关覆盖若干传感点，雨量和土壤温度比空气条件更重要。
- 没有可用外网、或数据不允许外传的场地——本地 ChirpStack 套餐两种情况都能覆盖。
- 已经在向云端上报的存量 SenseCAP 部署，想要一份本地看板和本地自动化，又不想搬动现有链路。

## 实测到什么程度

本方案**没有**接过真实 LoRaWAN 网络。下面全部来自一次本机冒烟：Mac 桌面 Docker 主机，
把构造的上行回放进 broker——这不是真机证据，也说明不了射频覆盖、节点容量或端到端延迟。

| 检查项 | 结果 | 条件 | 来源 |
|---|---|---|---|
| MQTT 自动发现创建实体 | 3 台设备共 15 个实体 | 一轮回放 13 条上行，覆盖三种来源格式（云、The Things Stack、ChirpStack） | 本机冒烟 2026-09-05——非真机 |
| 单位、device class、state class 生效 | 15 个全部与配置一致 | 从 Home Assistant `GET /api/states` 读回核对 | 本机冒烟 2026-09-05——非真机 |
| 去重与取最新值 | 唯一一个带两个时间戳的实体处理正确 | 回放里同一实体出现两次，较晚的那条胜出 | 本机冒烟 2026-09-05——非真机 |
| availability 翻成 offline | 15 个实体全部变成 `unavailable` | 测试时把阈值缩短到 60 s；watchdog 每 15 s 扫一次 | 本机冒烟 2026-09-05——非真机 |
| 阈值通知的建立与关闭 | 两个方向都验证过 | 土壤水分先低于阈值再回到阈值以上；空气温度越过阈值 | 本机冒烟 2026-09-05——非真机 |

没有测、因此不作任何声称的部分：通信距离、单网关能带多少节点、丢包与恢复、
网关重启时间、节点续航、端到端延迟，以及 SenseCAP OpenAPI 回填在真实账号上的表现。
桥的云端 source 从未持有过真实凭据。

## 输出接口

| 接口 | 主题 | 负载 |
|---|---|---|
| MQTT 自动发现 | `homeassistant/sensor/sensecap_<deveui>/<entity_key>/config` | retained 的发现配置，每个实体一条 |
| MQTT 状态 | `agri_env/sensecap_<deveui>/<entity_key>/state` | retained 的数值 |
| MQTT 可用性 | `agri_env/sensecap_<deveui>/availability` | retained 的 `online` 或 `offline` |

Home Assistant 的实体 ID 由设备名和实体名推导而来：`sensor.sensecap_<deveui>_<entity_key>`，
DevEUI 小写。这里刻意用完整 DevEUI——用缩短形式时，地址后缀相同的两个节点会撞车。

## 套餐怎么选

**SenseCAP 云**——节点已经在向云端上报、你只想要一份本地看板又不想动射频侧时选它。
它是唯一能显示安装之前那段历史的套餐，也是唯一需要出站外网的套餐。它还需要一对
SenseCAP API 密钥。

**自建 The Things Stack**——想把网络服务器攥在自己手里、并且愿意搭一个网关时选它：
CM4 主机上的 WM1302 集中器、packet forwarder，以及一套自带 Postgres 与 Redis 的 stack。
三者中安装工作量和资源占用都最重的一个。

**本地 ChirpStack**——网关本身就能当网络服务器时选它。在 M2 上，整个网络服务器就是
Web 界面里的一项设置，这是走到完全本地部署的最短路径；在装了 WM1302 的 CM4 主机上，
它是一套 Docker stack。无公网验收场景走的就是这个套餐。

## 使用注意

- **套餐 2 和 3 里 decoder 不是可选项。** SenseCAP 的上行是二进制的。
  没装 payload formatter（The Things Stack）或 device-profile codec（ChirpStack），
  网络服务器交给桥的就是一堆不含测量项的字节，一个实体也出不来。
  网络服务器没解出来的东西，桥恢复不了。
- **SenseCAP 云 MQTT 有两个域名在流传，都没有实测确认。** 部署步骤里两个都提供。
  如果桥的日志显示 DNS 或认证失败，改用另一个重新部署。
- **broker 是看板的单点。** 状态主题是 retained 的，所以 Home Assistant 重启后能恢复最后的值；
  但 broker 挂了，三个套餐都不会再有更新。
- **数值是原样透传的，不做换算。** 桥按 `measurementId` 配的单位贴标签，不缩放数字。
  如果某个型号上报的量纲不同，改 `assets/config/measurements.yaml` 即可，不用改代码。
- **改实体命名规则必须先清 retained 消息。** 自动发现配置是 retained 的，
  不同时清掉 broker 的 retained 消息和 Home Assistant 的实体注册表，旧主题重启后还会回来。
- **不要把 broker 暴露到公网。** 它涉及主机上 `.env` 里的凭据；
  ChirpStack 套餐里 LNS 侧的 broker 还在 compose 网络内不带认证运行。
  这两点在可信局域网内没问题，在别处不行。
- **桥的镜像还没发布。** `agri-env-bridge:0.1.0` 目前只是一个 tag 引用；
  部署前先本地构建，或者把 `BRIDGE_IMAGE` 指向你自己的 registry。

## 许可说明

`assets/config/measurements.yaml` 里 `measurementId` 到物理量的对照表，
读自 `Seeed-Solution/SenseCAP-Decoder` 仓库 commit `d0a2342` 的 decoder 源码。
**该仓库没有 LICENSE 文件**，README 里也没有许可段落；
全仓库唯一的许可声明在一个第三方贡献的文件头里，写的是 `Unlicensed for internal use`。
因此 decoder 的许可状态是**未确认**。

本方案不转发 decoder。它只用了 `id → 物理量` 这个事实性对应关系，
并为每条记录标注源文件与行号；Home Assistant 的 `device_class`、`unit_of_measurement`、
`state_class` 三列则取自 Home Assistant sensor 文档。
套餐 2 和 3 的部署指南链接上游仓库，而不是随方案分发那些 JavaScript。
要把 decoder 本身随部署一起分发，请先与 Seeed 确认许可立场。

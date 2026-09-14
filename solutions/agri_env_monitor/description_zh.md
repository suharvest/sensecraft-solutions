# 农业环境监测

## 它做什么

SenseCAP LoRaWAN 节点测量空气温湿度、土壤温度、水分、电导率、CO2 和雨量，本方案把这些读数显示在 Home Assistant 看板上，保留历史，数值越界时发通知。数据可以走 SenseCAP 云，也可以走自建的 The Things Stack 或 ChirpStack，后者可全程不联外网。

## 你会得到什么

- **现成看板**：空气温湿度、土壤温度、水分与电导率、雨量、电量与在线状态。
- **越界告警**：数值越过阈值时创建通知，恢复后自动关闭。
- **离线提示**：节点停止上报超过设定时长后显示为离线，保留最后一个值。
- **云端历史回填**：SenseCAP 云套餐首次启动时补齐安装前的历史数据。
- **切换路径不改看板**：三个套餐实体命名一致，从云端切到本地网络服务器，看板和自动化不用改。
- **可完全本地运行**：ChirpStack 套餐不需要云账号和外网连接。

## 适用场景

- 大棚：按土壤水分和电导率决定灌溉、追肥。
- 大田地块：一个网关覆盖多个传感点。
- 没有外网或数据不允许外传的场地（本地 ChirpStack 套餐）。
- 已向 SenseCAP 云上报、想加本地看板和自动化的存量部署。

## 实测效果

| 指标 | 效果 |
|---|---|
| 节点读数显示为看板实时数据 | **15/15** 实体 |
| 越界通知的建立与解除 | **两个方向都成立** |
| 节点停报后标为离线 | **15/15** 实体 |

测试方式为本机回放 3 台设备的上行，三条接入路径共 13 条上行；通信距离、节点容量、续航请按规格书取值并在现场实测。

## 输出接口

| 接口 | 内容 |
|---|---|
| MQTT `homeassistant/sensor/sensecap_<deveui>/<entity_key>/config` | Home Assistant 自动发现配置 |
| MQTT `agri_env/sensecap_<deveui>/<entity_key>/state` | 传感器数值 |
| MQTT `agri_env/sensecap_<deveui>/availability` | 节点在线状态 `online` / `offline` |

## 套餐怎么选

| | SenseCAP 云 | 自建 The Things Stack | 本地 ChirpStack |
|---|---|---|---|
| 适合 | 节点已在向云端上报 | 想自己管网络服务器 | 网关自带网络服务器（M2）或 R12 系列网关 |
| 需要外网 | 需要 | 不需要 | 不需要 |
| 安装前的历史 | 有 | 无 | 无 |
| 安装工作量 | 最小，需 SenseCAP API 密钥 | 最重 | M2 上最短 |

## 使用注意

- 套餐 2 和 3 必须在网络服务器上装 SenseCAP decoder，否则看板上没有任何实体。
- SenseCAP 云 MQTT 有两个域名，桥日志报 DNS 或认证失败时换另一个重新部署。
- broker 停止时三个套餐都不再更新数据。
- 改实体命名规则前，需同时清掉 broker 的 retained 消息和 Home Assistant 实体注册表。
- 不要把 broker 暴露到公网：ChirpStack 套餐 LNS 侧 broker 无认证。

## 许可说明

`assets/config/measurements.yaml` 的 `measurementId` 对照表读自 `Seeed-Solution/SenseCAP-Decoder`（commit `d0a2342`），该仓库没有 LICENSE 文件，许可状态未确认。本方案不转发 decoder，只使用 id 到物理量的对应关系，部署指南链接上游仓库；要随部署分发 decoder 本身，请先与 Seeed 确认许可。

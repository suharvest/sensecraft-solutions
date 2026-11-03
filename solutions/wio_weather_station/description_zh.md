# Wio Terminal 气象站与 SenseCAP 入门体验套装

## 方案概述

在专业微气象监测与物联网环境感知中，标准方案采用工业级气象传感器（如 SenseCAP ONE S700 / S1000 紧凑型气象传感器）直连 SenseCAP 平台（SenseCAP PaaS / Portal），实现户外全天候、高精度环境监测与集中资产管理。

然而在方案前期评估、研发调试或室内桌面监测中，用户往往缺少现成且昂贵的户外气象站硬件。为此，本方案提供 **Wio Terminal 气象站入门体验套装**：利用低成本自包含的 Wio Terminal（基于 120 MHz ATSAMD51P19A 与 RTL8720DN Wi-Fi）与 Grove 传感器，作为无工业气象站时的真实原型与体验套件。

本方案在完全脱网环境下亦可独立工作，无需任何外部服务器或 Home Assistant 实例支持。通过机身板载与 Grove 传感器采集大气环境与声学数据，在 2.4 寸 320×240 TFT LCD 彩色屏幕上呈现暗黑极客风格仪表盘，由五向摇杆实现 4 个监控页面的平滑交互。

当设备连接 2.4 GHz Wi-Fi 网络时，可作为物联网网关运行，遵循 Home Assistant MQTT Discovery 规范自动向局域网 Home Assistant 注册并上报全部遥测数据，并可通过 API / MQTT 桥接至 SenseCAP 气象云平台，提前跑通云端数据流与告警闭环。后续用户采购 SenseCAP ONE 工业气象站时，可直接平滑迁移，无需重构上层业务逻辑。

### 系统架构

```
+-------------------------------------------------------------+
|               气象监测标准演进体系 (Architecture)           |
+-------------------------------------------------------------+
  [工业标准方案]                            [入门体验套装]
 SenseCAP ONE 系列                       Wio Terminal 气象站
(S700/S1000 紧凑型气象站)                 (ATSAMD51 + Grove 传感器)
        |                                           |
(RS485 / Modbus / 4G)                  (脱网独立运行)    (Wi-Fi MQTT)
        |                                   |                |
        |                                   v                v
        |                          [2.4寸 LCD 暗色仪表盘] [Home Assistant 网关]
        |                          [4屏五向摇杆平滑交互]  [Lovelace 现代看板]
        |                                                    |
        +-----------------------+----------------------------+
                                |
                                v (统一纳管 / 云端同步)
            +---------------------------------------+
            | SenseCAP 气象云平台 (SenseCAP Portal) |
            | - 气象数据长期归档与趋势分析          |
            | - 阈值越界告警与 Open API 集成        |
            | - 支持从入门套件无缝升级至工业气象站  |
            +---------------------------------------+
```

## 核心优势

| 核心优势 | 具体说明 |
|---|---|
| 气象标准与平滑演进 | 依托 SenseCAP 气象平台体系，提供低成本桌面入门套装，后续可无缝升级接入 SenseCAP ONE 工业级气象站 |
| 零网络依赖独立运行 | 插入 5V USB Type-C 即可独立开箱工作，无需网关、云端账号或局域网环境 |
| 暗黑极客风彩屏交互 | 内置 2.4 寸 320×240 LCD 仪表盘，五向摇杆平滑切换 4 大专属监控界面 |
| 模块化 Grove 传感扩展 | 双 Grove 接口（I2C 与通用 GPIO/ADC），支持灵活扩展与采样刷新率自定义 |
| Home Assistant 原生联动 | 遵循 MQTT Discovery 规范，全自动无感注册环境与声学实体，告别手工 YAML |
| AI Agent 辅助看板定制 | 提供现成提示词模板，支持 Claude、ChatGPT、Copilot 一键生成专属 Lovelace 看板 |

### 独立运行与扩展能力

#### 1. 零网络依赖的自包含桌面监控
- **开机即用**：插入标准 5V USB Type-C 供电即可立即启动工作，无需 Wi-Fi 配网、云端账户或网关网桥介入。
- **硬件加速交互**：ATSAMD51 Cortex-M4F 芯片自主执行传感器轮询、数据校准、噪声 RMS 采样与 2.4 寸 TFT LCD 页面刷新闭环。
- **多页翻页控制**：机身正面五向摇杆支持向左/向右拨动，在 4 个独立全彩监控页面之间平滑切换。

#### 2. 模块化 Grove 扩展插槽与可配置刷新率
- **双 Grove 扩展接口**：
  - **左侧 Grove 接口（硬件 I2C）**：默认连接 BMP280 气压计；兼容各类 Grove I2C 模块，如 Grove - SGP30 / SCD30（空气质量与 CO2 监测）、Grove - 阳光传感器（SI1145）或外部 OLED 扩展屏。
  - **右侧 Grove 接口（通用 GPIO / ADC）**：默认连接 DHT11 温湿度计；亦可接入 Grove - 激光粉尘传感器（HM3301）、Grove - 土壤湿度传感器或微波雷达人体传感器。
- **采样与刷新率解耦可调**：
  - LCD 界面刷新率：默认 1 Hz，确保动态声压级指示条平滑跟手。
  - 气象传感器采样率：默认 2~5 秒平滑更新，兼顾数据精度与传感器发热控制。
  - MQTT 遥测上报间隔：可独立配置上报周期，按需平衡局域网带宽与功耗。

### LCD 仪表盘分页与交互

显示模块支持 4 个全彩界面，通过机身正面右下方的五向摇杆（向左 / 向右拨动）进行平滑翻页：

1. **第 0 页：综合概览（Overview）**：采用 2×2 网格卡片布局，同步显示温度（℃）、湿度（%）、气压（hPa）与光照强度（lx）。
2. **第 1 页：温湿度详情（Thermo & Hygro）**：大字号实时读数配合同心柱状刻度槽，并根据热力学指标实时评估体感状态。
3. **第 2 页：气压与声学（Baro & Noise）**：实时绘制气压趋势指标，下方搭载声级计动态指示条，分为五档声压分级：静音（<45 dBA）、舒适（45~55 dBA）、一般（55~65 dBA）、吵闹（65~75 dBA）与高噪警告（>75 dBA）。
4. **第 3 页：系统与诊断（System & MQTT）**：展示当前 DHCP 分配的 IP 地址、Wi-Fi RSSI 信号格、MQTT Broker 连接状态、遥测包累计发送计数以及 Home Assistant 自动发现广播状态。

顶部物理按键功能：
- **按键 A（最右侧）**：立即强制触发一次 MQTT 数据上报。
- **按键 C（最左侧）**：重新发送 Home Assistant Auto-Discovery 自动发现注册报文。

### Home Assistant MQTT 自动发现协议

启用网络上报后，设备连接网络并接入 MQTT Broker，会自动向对应主题推送包含 `retain: true` 的标准声明报文：

- **自动发现主题**：`homeassistant/sensor/Wio-Weather-<MAC>/<component>/config`
- **遥测数据主题**：`wio-weather/telemetry`
- **在线状态与遗嘱主题（LWT）**：`wio-weather/status`（状态值为 `online` 或 `offline`）

Home Assistant 自动生成的实体清单：

| 实体名称 | 实体唯一标识 | 设备类型 (Device Class) | 单位 |
|---|---|---|---|
| 温度 (Temperature) | `sensor.wio_weather_<mac>_temperature` | `temperature` | `°C` |
| 湿度 (Humidity) | `sensor.wio_weather_<mac>_humidity` | `humidity` | `%` |
| 气压 (Barometric Pressure) | `sensor.wio_weather_<mac>_pressure` | `atmospheric_pressure` | `hPa` |
| 环境光照 (Ambient Light) | `sensor.wio_weather_<mac>_illuminance` | `illuminance` | `lx` |
| 环境噪声 (Ambient Noise) | `sensor.wio_weather_<mac>_ambient_noise` | `sound_pressure` | `dBA` |
| Wi-Fi 信号 (Wi-Fi Signal) | `sensor.wio_weather_<mac>_wifi_rssi` | `signal_strength` | `dBm` |

### AI Agent 辅助看板定制

方案提供完整的 AI Agent 提示词模板，用户可直接复制给 Claude、ChatGPT 或 Home Assistant Copilot，生成匹配个人审美与空间风格的 Lovelace 仪表盘配置。提示词涵盖完整实体规范：
- `sensor.wio_weather_station_temperature`：-10 ~ 50 °C，分级舒适区颜色刻度
- `sensor.wio_weather_station_humidity`：0 ~ 100%，适宜区间标示
- `sensor.wio_weather_station_pressure`：950 ~ 1050 hPa 气压计
- `sensor.wio_weather_station_light`：0 ~ 10000 lx 光照度
- `sensor.wio_weather_station_noise`：30 ~ 100 dBA 声压级彩标
- `sensor.wio_weather_station_status`：在线连通性状态指示
- 24 小时温湿度气压联动历史曲线（`history-graph`）

## 典型场景

| 场景 | 怎么用 |
|---|---|
| 气象站方案快速评估与原型验证 | 在暂无现成户外工业气象站时，作为低成本真机体验套装，快速跑通从端侧传感、本地多屏交互到 Home Assistant 与 SenseCAP 平台的数据流与告警链路 |
| 桌面独立微型气象站 | 放置于办公桌或床头柜，独立通电即可实时监控小环境温湿度、气压与噪声舒适度，不依赖任何局域网与外部服务 |
| Home Assistant 智能家居环境节点 | 通过局域网 Wi-Fi 将室内环境与声学数据同步至 Home Assistant，联动加湿器、除湿机、空调或照明设备 |
| 专注学习与静音环境监测 | 凭借板载驻极体麦克风与实时声级计分级，用于书房、琴房、录音室或静音自习室的噪声分贝监测与超标提示 |
| 嵌入式创客与 STEM 教学实训 | 基于开放架构与丰富 Grove 接口，作为物联网节点开发、多页 GUI 设计与传感联动的教学教具 |

## 使用须知

### 硬件连线与引脚分配

硬件连接使用 Wio Terminal 机身底部的标准 4-pin Grove 接口：

| 传感器 / 模块 | 物理接口 | 接口协议 | 硬件引脚分配 | 工作参数 |
|---|---|---|---|---|
| Grove BMP280 | 左侧 Grove 口 | 硬件 I2C | SCL (D5), SDA (D4) | 地址 `0x76` 或 `0x77`，量程 300~1100 hPa |
| Grove DHT11 | 右侧 Grove 口 | 数字 GPIO | Signal (D0), VCC (3.3V), GND | 温度 0~50 °C (±2 °C)，湿度 20~90% RH (±5%) |
| 机身光敏传感器 | 内部板载 | 模拟 ADC | `WIO_LIGHT` (PD01 / A0) | 映射为环境照度（单位：lx） |
| 机身麦克风 | 内部板载 | 模拟 ADC | `WIO_MIC` (PD08 / A2) | RMS 采样计算声压级（单位：dBA） |

> 当使用 Grove Beginner Kit 套件中的传感器模块时，建议沿 PCB 邮票孔将所需模块掰下独立接线，或确保 Beginner Kit 底板的 Micro-USB 接口处于断电状态，避免与 Wio Terminal 发生双电源总线冲突。

### 网络与运行要求

- **供电要求**：使用标准 5V USB Type-C 数据线供电（推荐供电电流 >= 500mA）。
- **Wi-Fi 网络（可选）**：设备接入局域网需 2.4 GHz Wi-Fi（不支持 5 GHz 频段）。脱网独立运行显示时无需 Wi-Fi。
- **Home Assistant 与 MQTT Broker（可选）**：接入智能家居时，局域网中须部署有可达的 MQTT Broker（如 Home Assistant 内置 Mosquitto MQTT 插件）。

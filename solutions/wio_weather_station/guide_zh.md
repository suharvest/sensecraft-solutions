## 套餐: 小型气象站与环境监测标准方案 {#default}

标准气象监测方案采用 SenseCAP 工业级气象传感器直连 SenseCAP 平台。针对暂无现成户外气象站的用户，本方案提供基于 Wio Terminal 与 Grove 传感器的自包含桌面入门体验套装。即使在完全脱网状态下，设备亦可独立驱动 2.4 寸暗色 LCD 仪表盘（五向摇杆 4 屏平滑切换），并支持按需接入 Home Assistant MQTT 遥测与 SenseCAP 气象云平台。

| 设备 | 作用 |
|---|---|
| Wio Terminal | 桌面入门主控：采集传感器数据、驱动 2.4 寸暗色 LCD 仪表盘、发布 MQTT 遥测 |
| Grove Beginner Kit (DHT11 与 BMP280) | 环境温湿度与大气气压传感采集（无工业气象站时的低成本真实体验套件） |
| SenseCAP 气象平台 (SenseCAP Portal) | 气象站标准云端纳管平台：数据长期归档、API 开放与告警联动（后续可平滑升级接入 SenseCAP ONE 工业气象站） |

**你会得到：**
- 完全自包含独立运行的 Wio Terminal 2.4 寸 TFT LCD 现代暗色极客风格实时仪表盘（五向摇杆左右切页）
- 可选接入 Home Assistant 的自动发现实体：温度、湿度、气压、光照度、环境噪声声压级与 Wi-Fi 信号强度
- 可自定义配置的采样与刷新周期，以及机身物理按键强制刷新与广播控制
- 开箱即用的 Lovelace YAML 仪表盘与 AI Agent 定制提示词模板，实现极速界面搭建
- 对接 SenseCAP 气象云平台的上报与管理链路，以及升级至 SenseCAP ONE 工业气象站的标准演进方案

## 步骤 1: 烧录 Wio Terminal 气象站固件 {#flash_firmware type=wio_terminal_usb required=true config=devices/wio_terminal_deploy.yaml}

通过 USB CDC 串口将气象站固件烧录至 Wio Terminal。

### 前置条件

1. 使用 USB Type-C 数据线将 Wio Terminal 连接至计算机。
2. 若需接入 Home Assistant，准备好 2.4 GHz Wi-Fi 名称与密码。
3. 确保 Home Assistant MQTT Broker (Mosquitto) IP 地址与端口网络可达（本地独立监控可不连）。
4. 若烧录工具未自动识别，可连续向下拉动两次 Wio Terminal 电源开关进入 Bootloader 模式（蓝色指示灯呼吸闪烁）。

### 接线

1. 使用 4-pin Grove 连接线将 Grove BMP280 气压传感器连接至 Wio Terminal **左侧 Grove 接口（I2C）**。
2. 使用 4-pin Grove 连接线将 Grove DHT11 温湿度传感器连接至 Wio Terminal **右侧 Grove 接口（D0/A0）**。
3. 光照与环境噪音监测默认使用 Wio Terminal 机身板载传感器，无需额外飞线。
4. 使用 Grove Beginner Kit 模块时切勿为底板 Micro-USB 供电，避免双电源倒灌。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 找不到串口设备 | 检查 USB 线是否具备数据传输能力；连续向下拉动电源开关两次强制进入 Bootloader 模式 |
| 烧录超时或写入失败 | 确保没有 Arduino IDE 串口监视器或其他终端程序占用串口通道 |
| Wi-Fi 连不上 | Wio Terminal RTL8720DN 仅支持 2.4 GHz Wi-Fi 网络；核对 SSID 与密码是否正确 |
| 传感器数值异常 | 检查 Grove 接线是否插紧；确认 BMP280 接左侧 I2C 口、DHT11 接右侧 D0 口 |

---

## 步骤 2: 配置 Home Assistant 智能网关与气象看板 {#ha_setup type=ha_integration required=false config=devices/ha_setup.yaml}

自动配置 Home Assistant：一键安装并启动 Mosquitto MQTT Broker 插件、添加 MQTT 集成条目、配置高温自动告警规则，并创建独立的 `/wio-weather` 现代暗色气象仪表盘。

### 前置条件

1. Home Assistant 处于运行状态，且局域网网络可达。
2. 拥有 Home Assistant 管理员账号与密码。
3. Wio Terminal 已完成烧录并接入相同网络环境。

### 自动化配置内容

1. **Mosquitto MQTT 代理**: 自动安装并启动官方 MQTT 插件。
2. **MQTT 基础集成**: 自动完成与 MQTT Broker 的 Config Flow 对接。
3. **自动化规则**: 当检测到环境气温超过 35°C 时自动发送通知。
4. **独立气象看板**: 自动创建 `/wio-weather` Lovelace 仪表盘，展示气温、湿度、气压、光照度、声压级及 Wi-Fi 信号强度等核心指标。

### 常见问题与排错

| 现象 | 解决方案 |
|---|---|
| 登录认证失败 | 检查输入的 Home Assistant 管理员账号及密码是否正确 |
| 实体发现超时 | 轻按 Wio Terminal 顶部的按键 C，重新广播 MQTT 自动发现配置包 |
| 看板冲突拒绝写入 | 确保 Home Assistant 中不存在他方占用且未受 SenseCraft 托管的 `/wio-weather` 看板 |

---

## 步骤 3: 通过 AI Agent 定制看板样式 {#customize_ha_dashboard type=manual required=false config=devices/customize_ha_dashboard.yaml}

借助 AI 编程助手（Claude、ChatGPT 或 Home Assistant Copilot）为 Wio Terminal 气象站定制个性化 Lovelace 仪表盘。

### 前置条件

1. Home Assistant 已就绪，且在 **开发者工具 -> 状态** 或 **配置 -> 设备与服务 -> MQTT** 中可查看到对应气象站实体。
2. 确认你的具体实体 ID（默认命名为 `sensor.wio_weather_station_*` 或带有 MAC 后缀如 `sensor.wio_weather_<mac>_*`）。
3. 拥有 Home Assistant 仪表盘的编辑修改权限。

### AI Agent 提示词模板 (Prompt)

复制以下结构化提示词模板发送给你的 AI Agent（Claude、ChatGPT 或 Home Assistant Copilot），让其根据你的空间主题风格快速生成 Lovelace YAML 配置：

```text
你是一名精通 Home Assistant 界面定制的专家。请为我的 Wio Terminal 桌面气象环境监控站编写一份现代 Lovelace 仪表盘 YAML 配置代码。

气象站实体清单如下：
1. 温度传感器：
   - 实体 ID：sensor.wio_weather_station_temperature
   - 单位：°C（量程：-10 ~ 50 °C）
   - 卡片建议：仪表盘 Gauge 卡片，舒适区绿色（18-26 °C），偏热黄色（26-32 °C），高温红色（>32 °C）。
2. 湿度传感器：
   - 实体 ID：sensor.wio_weather_station_humidity
   - 单位：%（量程：0 ~ 100%）
   - 卡片建议：仪表盘 Gauge 卡片，人体适宜区间 40%~70% 绿色标示。
3. 大气气压传感器：
   - 实体 ID：sensor.wio_weather_station_pressure
   - 单位：hPa（参考量程：950 ~ 1050 hPa）
   - 卡片建议：Gauge 卡片或数值统计卡片，带趋势指标。
4. 环境光敏传感器：
   - 实体 ID：sensor.wio_weather_station_illuminance
   - 单位：lx（参考量程：0 ~ 10000 lx）
   - 卡片建议：紧凑型 Entities 实体行，带 mdi:white-balance-sunny 动态图标。
5. 环境噪声分贝传感器：
   - 实体 ID：sensor.wio_weather_station_ambient_noise
   - 单位：dBA（量程：30 ~ 100 dBA）
   - 卡片建议：声级计风格 Gauge 卡片，静音（<55 dBA 绿色）、适中（55-70 dBA 黄色）、吵闹（>70 dBA 红色）。
6. Wi-Fi 信号强度：
   - 实体 ID：sensor.wio_weather_station_wifi_rssi
   - 单位：dBm
   - 卡片建议：实体行或卡片，显示信号强度。

排版要求：
- 使用 vertical-stack 与 horizontal-stack 组织多行卡片网格。
- 附带一张 24 小时历史趋势折线图（history-graph），对比展示温湿度与气压的昼夜走势。
- 风格现代极客、配色清晰，适配桌面触控屏或移动端查看。
- 输出可直接粘贴至 Home Assistant“手动”（Manual）卡片编辑器的纯 YAML 代码。
```

### 开箱即用 Lovelace 仪表盘 YAML 示例

你也可以直接复制以下完整 Lovelace YAML 代码快速应用：

```yaml
type: vertical-stack
title: Wio Terminal 气象环境监控站
cards:
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.wio_weather_station_temperature
        name: 温度
        min: -10
        max: 50
        needle: true
        severity:
          green: 18
          yellow: 26
          red: 32
      - type: gauge
        entity: sensor.wio_weather_station_humidity
        name: 相对湿度
        min: 0
        max: 100
        needle: true
        severity:
          red: 20
          green: 40
          yellow: 70
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.wio_weather_station_pressure
        name: 大气气压
        min: 900
        max: 1100
        needle: true
      - type: gauge
        entity: sensor.wio_weather_station_ambient_noise
        name: 环境噪声
        min: 30
        max: 100
        needle: true
        severity:
          green: 30
          yellow: 55
          red: 70
  - type: entities
    title: 运行状态与光照
    show_header_toggle: false
    entities:
      - entity: sensor.wio_weather_station_wifi_rssi
        name: Wi-Fi 信号强度
        icon: mdi:wifi
      - entity: sensor.wio_weather_station_illuminance
        name: 环境光照度
        icon: mdi:white-balance-sunny
  - type: history-graph
    title: 24 小时环境走势
    hours_to_show: 24
    refresh_interval: 60
    entities:
      - entity: sensor.wio_weather_station_temperature
        name: 温度 (°C)
      - entity: sensor.wio_weather_station_humidity
        name: 湿度 (%)
      - entity: sensor.wio_weather_station_pressure
        name: 气压 (hPa)
```

### 部署完成

1. 进入 Home Assistant 目标仪表盘，点击右上角铅笔图标（**编辑仪表盘**）。
2. 点击右下角 **+ 添加卡片**，滑动到最下方选择 **手动**（YAML 编辑卡片）。
3. 将生成的或上方示例 YAML 代码粘贴到编辑器中，确认右侧实时预览无误后点击 **保存**。

### 故障排查

| 现象 | 处理 |
|---|---|
| 卡片提示“实体不可用”或“找不到实体” | 打开 Home Assistant **开发者工具 -> 状态**，确认实体 ID 名称；若实际实体带有设备 MAC 后缀，请在 YAML 中批量替换对应的 `sensor.wio_weather_station_*` 名称 |
| 仪表盘刻度区间与本地环境不符 | 直接编辑 Lovelace YAML 中的 `min`、`max` 和 `severity` 阈值，按季节或地域气候调整 |
| 历史曲线图显示空白 | 确认 Home Assistant 历史记录（recorder）已正常启用，传感器上报数分钟后即可绘制连续历史曲线 |

---

## 步骤 4: 在 Home Assistant 看板中验证数据 {#verify_ha type=web_dashboard required=false config=devices/verify_ha.yaml}

打开 Home Assistant 网页端，验证已部署的 `/wio-weather` 气象仪表盘、MQTT 自动发现与各传感器实时遥测数据。

### 验证要点

1. 从 Home Assistant 侧边栏打开 `/wio-weather` 看板，或直接访问 `http://<ha-host>:<ha-port>/wio-weather`。
2. 检查温湿度仪表盘是否随着数据上报实时更新。
3. 检查大气气压、环境噪声、环境光照与 Wi-Fi 信号强度卡片显示。
4. 确认 24 小时环境走势图正常绘制历史数据。

### 常见问题与排错

| 现象 | 解决方案 |
|---|---|
| 看板卡片显示空白 | 确认 Wio Terminal 已连接 Wi-Fi 并持续发送 MQTT 数据包；轻按按键 C 重新广播自动发现配置 |
| 网页无法访问 | 检查 Home Assistant 服务运行状态与主机端口网络连通性 |

---

## 步骤 5: 接入 SenseCAP 平台与工业演进 {#connect_sensecap type=web_dashboard required=false config=devices/connect_sensecap.yaml}

气象站方案标准面向生产环境采用 SenseCAP 工业级气象传感器（如 SenseCAP ONE S700 / S1000 紧凑型气象站）直连 SenseCAP 平台（SenseCAP PaaS / Portal），实现户外恶劣环境下的高可靠气象监测与云端统一资产管理。

本 Wio Terminal 套装作为低成本入门评估工具，在完成桌面采集与 Home Assistant 本地联动后，亦可通过 SenseCAP 开放平台将气象数据上报至云端统一归档，便于提前跑通多端查看、API 告警分发与历史分析链路。

### 操作步骤

1. 点击下方 **打开 SenseCAP 平台** 按钮，访问 [SenseCAP Portal](https://sensecap.seeed.cc/)；
2. 登录或注册 SenseCAP 账户，进入 **Security -> Access API keys** 获取 API 访问密钥；
3. 在 Home Assistant 中通过 REST API / MQTT Forwarder 或 Node-RED 流，将 `sensor.wio_weather_station_*` 数据定时同步至 SenseCAP 数据流；
4. 在 SenseCAP Portal 监控大屏上实时查看环境指标趋势与设备在线心跳；
5. **工业平滑升级**：当后续采购 SenseCAP ONE 工业级气象站（支持超声波风速风向、光学雨量、高精度气压温湿度等）时，直接扫码添加设备至同一 SenseCAP 账户，原有业务系统与报表无需重新开发。

### 常见问题与排错

| 现象 | 解决方案 |
|---|---|
| SenseCAP API 鉴权失败 | 检查输入的 Access ID 与 Access Key 是否具备设备数据读写权限 |
| 无法在云端看到实时曲线 | 确认本地网络可访问外网 MQTT / HTTPS 端点，检查防火墙 8883/443 端口放行状态 |
| 工业升级选型建议 | 室外微气象监测推荐 SenseCAP ONE S700（7合1紧凑型）或 S1000（10合1全能型，含 PM2.5/PM10/CO2） |


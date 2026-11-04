## 套餐: 墨水屏智能家居面板 {#usb_candidate}

通过 USB 连接 E1003 墨水屏面板并接入 Home Assistant。安装器会自动下载并烧录面板出厂固件，部署或连接 Home Assistant，并自动完成面板联动。

> 注意：请确保通过 USB 连接 reTerminal E1003 面板。烧录步骤将直接从 CDN 下载并安装固件。

## 步骤 1: 安装 E1003 面板程序 {#e1003_usb type=esp32_usb required=true verify=true config=devices/e1003_usb.yaml}

在部署工具中选择串口并点击 **部署**，等待固件安装与重启校验完成。

### 前置条件

- 一台 reTerminal E1003 面板与一根 USB 数据线。
- 电脑、E1003 面板与 Home Assistant 处于同一局域网。

### 接线

1. 使用 USB 数据线连接 E1003 底板的 USB-UART 口与电脑。
2. 在 App 的串口列表中选择该设备端口（若列表为空，点击同行的“刷新”）。

### 烧录

1. 在串口列表中选择连接的 E1003 设备端口。
2. 点击 **安装** / 部署。安装器将从 CDN 下载固件并以 115200 波特率烧录至面板。
3. 保持设备通电，直到烧录与重启校验完成。

<details>
<summary>技术详情</summary>
<p>固件大小 1,365,696 字节，SHA-256 为 <code>1aee4b0c4864181ef9b7cf88bd2c6dcf690d9eafd047badcfbbe8bb6959fd927</code>。烧录参数为 115200 波特率、偏移量 0x0、不全片擦除并保留 NVS。</p>
</details>

### 部署完成

1. **Wi-Fi**：连接面板上显示的 `reterminal-e1003-xxxxxx` 热点（无密码），浏览器打开 `192.168.4.1`，选择 2.4 GHz Wi-Fi。面板随后显示 IP 和 `HA WAITING`。
2. **Home Assistant**：执行步骤 3，或手动添加 **ESPHome** 集成，填面板 IP（端口 `6053`）。面板显示 `HA CONNECTED`。无需 API 密钥或额外权限。
3. **灯光**：[导入蓝图](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml)并创建自动化，选择要控制的灯，以及这台面板的 `Main light command`、`Main light state`、`Main light value`。在 Home Assistant 里切换一次灯，让屏幕同步。以后换灯，直接在该自动化里改。

**更换 Wi-Fi**：在屏幕上连续点两次 Wi-Fi 区域（8 秒内），再重复第 1 步。配对信息保留；若 Home Assistant 没有重连，在 ESPHome 条目上用 **重新配置** 填新 IP。

**绿色键**：单击整屏刷新（清除残影）；长按 3 秒重启。

### 故障排查

| 现象 | 处理方式 |
| --- | --- |
| 找不到设备串口 | 点击刷新；使用支持数据传输的 USB 线；退出占用串口的其它程序 |
| 写入失败 | 按提示信息处理后重试，切勿擦除 NVS |
| 一直停在 `HA WAITING` | 让 Home Assistant 与面板处于同一局域网，用屏幕上的 IP 手动添加 ESPHome |
| 灯不响应 | 确认自动化使用的是该蓝图，且三个实体都选自这台面板 |


---

## 步骤 2: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

在本地或远程 Docker 主机上部署 Home Assistant。如果该主机 8123 端口已运行 Home Assistant，本步骤将自动检测并跳过。

> **宿主平台限制**：Home Assistant 容器依赖 Linux 原生 host 网络（`network_mode: host`）实现 mDNS 与局域网设备自动发现。**本地安装仅支持 Linux 宿主环境**。在 macOS 或 Windows 环境下，Docker Desktop 无法提供原生 host 网络，请**取消勾选本步骤以跳过**，或选择 `ha_remote` 部署到局域网内的独立 Linux 主机（如树莓派、reComputer），也可直接复用局域网中已有的 Home Assistant 实例。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 8123 端口上已有 Home Assistant | 本步骤会检测到已运行的实例并跳过安装，直接进入下一步。 |
| 在 macOS 或 Windows 上本地安装失败 | 容器使用主机网络模式，Docker Desktop 不提供该模式。请选择远程部署目标（Raspberry Pi、reComputer 等 Linux 主机），或使用已有的 Home Assistant。 |

### 部署目标 {#ha_local type=local config=devices/ha_host.yaml}

在本地 Linux 机器上部署 Home Assistant（仅支持 Linux host 网络，macOS/Windows 环境请跳过）。

### 部署目标 {#ha_remote type=remote config=devices/ha_host.yaml default=true}

通过局域网在远程 Linux 主机（如 Raspberry Pi、reComputer）上部署 Home Assistant。

---

## 步骤 3: 将 E1003 接入 Home Assistant（可选） {#connect_ha type=ha_integration required=false config=devices/ha_integration.yaml}

通过 Home Assistant 自动化 Config Flow API 将已配网的 E1003 面板直接接入 Home Assistant。随后导入灯光蓝图（步骤 1“部署完成”）。

### 前置条件

- E1003 已开机并接入局域网 Wi-Fi。
- Home Assistant 正常运行且网络可达。
- Home Assistant 管理员用户名与密码。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| Home Assistant 登录失败 | 请使用 Home Assistant 管理员账号，并确认本机能访问该实例。 |
| 找不到 E1003 面板 | 面板需已开机并连接到同一局域网的 2.4 GHz Wi-Fi。否则在 Home Assistant 中手动添加 ESPHome 集成并填写面板 IP（Native API 无需密钥）。 |

## 套餐: 彩屏智能家居面板 {#indicator_panel}

通过 USB 烧录 SenseCAP Indicator，并经 ESPHome 集成接入 Home Assistant，无需 MQTT broker。

## 步骤 1: 安装 Indicator 面板程序 {#indicator_usb type=esp32_usb required=true verify=true config=devices/indicator_usb.yaml}

连接 Indicator 的 USB-C 口，选择串口（列表中没有时手动填写），点击 **部署**，保持连接直到校验完成。

### 前置条件

- 一台 SenseCAP Indicator（D1 / D1S / D1Pro / D1L）与一根 USB 数据线。
- Indicator 与 Home Assistant 处于同一局域网。

### 部署完成

1. 在设备屏幕（Settings）接入 2.4 GHz Wi-Fi，并记下 Settings 中显示的 IP。
2. 执行步骤 3，或在 Home Assistant 中手动添加 **ESPHome** 集成，填该 IP 和端口 `6053`，加密密钥留空。
3. 设备页会显示 12 个实体（温度、湿度、CO2、tVOC、6 个开关、2 个数值）。Home Assistant 不会自动生成仪表盘卡片，按需自行添加。

> **注意**：未设置加密密钥时连接为明文，同一局域网内任何人都能读取并控制面板。请在可信网络中使用，或在串口控制台用 `native psk <base64>` 设置密钥，并在 Home Assistant 中填入同一密钥。

MQTT 为可选，沿用 topic `indicator/sensor`、`indicator/switch/set`、`indicator/switch/state`。在 Settings → MQTT broker 填入 broker，或在串口控制台用 `setmqtt` 配置。

### 故障排查

| 现象 | 处理方式 |
| --- | --- |
| 找不到设备串口 | 点击刷新或手动填写端口；使用支持数据传输的 USB 线 |
| Home Assistant 没有发现设备 | 手动添加 ESPHome，填 Indicator 的 IP 和端口 `6053`（自动发现依赖局域网 mDNS） |

---

## 步骤 2: 部署 Home Assistant（可选） {#indicator_deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

在 Docker 主机上部署 Home Assistant。8123 端口已运行时自动跳过。本地安装仅支持 Linux；macOS/Windows 请选择远程目标。

### 部署目标 {#indicator_ha_local type=local config=devices/ha_host.yaml}

在本机（Linux）部署。

### 部署目标 {#indicator_ha_remote type=remote config=devices/ha_host.yaml default=true}

在远程主机（如 Raspberry Pi、reComputer）部署。

---

## 步骤 3: 将 Indicator 接入 Home Assistant（可选） {#indicator_connect_ha type=ha_integration required=false config=devices/indicator_ha_integration.yaml}

自动将 Indicator 作为 ESPHome 设备添加到 Home Assistant。

### 前置条件

- Indicator 已接入 Wi-Fi，并已知其 IP。
- Home Assistant 正常运行且网络可达，并有管理员账号。

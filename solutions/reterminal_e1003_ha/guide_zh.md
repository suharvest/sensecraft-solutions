## 套餐: 智能家居控制面板 {#usb_candidate}

通过 USB 连接 E1003 面板并接入 Home Assistant。安装器会自动下载并烧录面板出厂固件，部署或连接 Home Assistant，并自动完成面板联动。

> 注意：请确保通过 USB 连接 reTerminal E1003 面板。烧录步骤将直接从 CDN 下载并安装 0.2.1 固件。

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
2. 点击 **安装** / 部署。安装器将从 CDN 下载 0.2.1 固件并以 115200 波特率烧录至面板。
3. 保持设备通电，直到烧录与重启校验完成。

<details>
<summary>技术详情与接入依赖</summary>
<p>参考固件 0.2.1 固定使用明文 native API，不提供 API 加密选项或密钥导出。</p>
<p>固件大小 1,337,056 字节，SHA-256 为 <code>472fea16c509b46ecb04d6636a8d8acbc05756ce02157d20fd40eaf483401291</code>。烧录参数为 115200 波特率、偏移量 0x0、不全片擦除并保留 NVS。</p>
<p>现有构建、软件与 CDN 发布检查均已通过；物理触摸、真实 HA 控灯及屏幕双向同步可在实机上进行体验验证。</p>
</details>

### 部署完成

1. **配网引导**：固件烧录完成后，设备可通过 USB 串口以 115200 波特率运行 Improv Serial 协议一键配置 Wi-Fi，或连接面板广播的临时 ESPHome 热点通过 Captive Portal 网页配置 2.4 GHz Wi-Fi（不支持纯 5 GHz 频段）。配网成功后面板将连接局域网并获取 IP 地址。
2. **设备接入**：若未执行步骤 3 自动接入，打开 Home Assistant，进入“设置 → 设备与服务 → 集成”，添加 ESPHome 设备并填入面板 IP 地址（Native API 无需密钥）。
3. **配置两步法绑定目标灯（无需创建自动化）**：固件通过 Native API 原生调用 Home Assistant action，由板载配置实体直接指定目标灯具，无需在 HA 中手动创建任何 Automation 规则：
   - **第一步（开启动作权限）**：在 Home Assistant 的 ESPHome 集成中找到 E1003 设备卡片，点击齿轮或选项，勾选开启 **“允许设备执行 Home Assistant 动作”**（Allow the device to perform Home Assistant actions）；
   - **第二步（写入目标灯 ID）**：在 E1003 设备的配置实体中找到目标灯实体（`text.e1003_target_light`），填入目标灯具实体 ID（例如 `light.living_room`）。固件将通过 Native API 原生控制该目标灯具。
4. **物理触控验收**：
   - 轻触面板开关键（Toggle），确认目标灯具能够实时开关；
   - 分别按压 25%、50%、75%、100% 亮度区域，确认目标灯平滑切换亮度，完成物理触控闭环。

> **注意**：面板目前仅定义了这五个触控区域，其他图标为静态常显展示。

### 故障排查

| 现象 | 处理方式 |
| --- | --- |
| 找不到设备串口 | 点击刷新按钮；检查 USB 数据线是否支持数据传输；退出可能占用串口的其它程序 |
| 配置或写入失败 | 根据界面上的具体错误信息处理后重试，切勿全片擦除 NVS |
| 界面提示正在保存或重启 | 保持设备供电，耐心等待读回并显示最终验证状态 |
| 按键无反应或灯具不响应 | 确认 ESPHome 设备设置中已开启“允许设备执行 Home Assistant 动作”；检查 `text.e1003_target_light` 实体中填写的目标灯 ID 正确且实体存在；确认面板与 HA 处于同一局域网并正常在线 |

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

通过 Home Assistant 自动化 Config Flow API 将已配网的 E1003 面板直接接入 Home Assistant。

### 前置条件

- E1003 已开机并接入局域网 Wi-Fi。
- Home Assistant 正常运行且网络可达。
- Home Assistant 管理员用户名与密码。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| Home Assistant 登录失败 | 请使用 Home Assistant 管理员账号，并确认本机能访问该实例。 |
| 找不到 E1003 面板 | 面板需已开机并连接到同一局域网的 2.4 GHz Wi-Fi。否则在 Home Assistant 中手动添加 ESPHome 集成并填写面板 IP（Native API 无需密钥）。 |

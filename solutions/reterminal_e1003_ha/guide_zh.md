## 套餐: 配置 E1003 {#usb_candidate}

通过 USB 连接 E1003 面板并接入 Home Assistant。安装器会自动检查固件并在需要时安装，部署或连接 Home Assistant，并自动完成面板联动。

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

1. 设备首次配网时，可通过 Improv Serial 或 ESPHome 热点（Captive Portal）配置 2.4 GHz Wi-Fi。
2. 若未执行步骤 3 自动接入，打开 Home Assistant，在“设置 → 设备与服务 → 集成”中添加 ESPHome 设备，填入面板 IP 地址（无需 API 密钥）。
3. 在 Home Assistant 中创建自动化（“设置 → 自动化与场景 → 创建自动化”）：
   - **触发条件**：选择 E1003 设备的按键或状态变化（例如开关按键或亮度滑块）。
   - **动作**：调用服务 `light.toggle` 或 `light.turn_on` 控制目标灯光实体（例如 `light.living_room`）。
4. 按压面板上的开关键以及 25% / 50% / 75% / 100% 亮度区域测试调光。

> **注意**：面板目前仅定义了这五个触控区域，其他图标为静态展示。

### 故障排查

| 现象 | 处理方式 |
| --- | --- |
| 找不到设备串口 | 点击刷新按钮；检查 USB 数据线是否支持数据传输；退出可能占用串口的其它程序 |
| 配置或写入失败 | 根据界面上的具体错误信息处理后重试，切勿全片擦除 NVS |
| 界面提示正在保存或重启 | 保持设备供电，耐心等待读回并显示最终验证状态 |
| 按键无反应或灯具不响应 | 确认 Home Assistant 中的自动化触发条件与控制实体配置正确；检查 ESPHome 设备设置中是否开启“允许设备执行动作” |

---

## 步骤 2: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

在本地或远程 Docker 主机上部署 Home Assistant。如果该主机 8123 端口已运行 Home Assistant，本步骤将自动检测并跳过。

### 部署目标 {#ha_local type=local config=devices/ha_host.yaml default=true}

在本地机器上部署 Home Assistant。

### 部署目标 {#ha_remote type=remote config=devices/ha_host.yaml}

通过局域网在远程主机（如 Raspberry Pi、reComputer）上部署 Home Assistant。

---

## 步骤 3: 将 E1003 接入 Home Assistant（可选） {#connect_ha type=ha_integration required=false config=devices/ha_integration.yaml}

通过 Home Assistant 自动化 Config Flow API 将已配网的 E1003 面板直接接入 Home Assistant。

### 前置条件

- E1003 已开机并接入局域网 Wi-Fi。
- Home Assistant 正常运行且网络可达。
- Home Assistant 管理员用户名与密码。

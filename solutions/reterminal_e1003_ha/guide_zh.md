## 套餐: 配置 E1003 {#usb_candidate}

连接设备，填写要控制的灯。App 会自动检查并按需安装固件。

> 技术演示候选，正式部署尚未开放；以下操作用于兼容的测试 App。

## 步骤 1: 连接设备 {#flash_panel type=manual required=true config=devices/review_flash.yaml}

连接 USB，选择设备串口。

### 前置条件

准备 USB 数据线和一盏已接入 HA 的调光灯。电脑、设备和 HA 需在同一可达局域网。

### 接线

1. 连接 E1003 底板 USB-UART 口与电脑。
2. 在串口选择行选择设备；列表未更新时，点击同一行的“刷新”。
3. 填写“按钮控制的灯”：从 HA 的实体设置复制 <code>light.*</code> ID，如 <code>light.bedroom</code>。这是手动输入，不会自动发现灯具。

<details>
<summary>Wi-Fi：已有网络可留空</summary>
<p>如需沿用设备保存的网络，名称和密码可留空；这不表示 App 已识别设备当前网络。</p>
<p>首次配置或更换网络时，填写 2.4 GHz Wi-Fi 名称和密码。密码输入默认遮蔽。</p>
</details>

### 故障排查

| 问题 | 处理 |
| --- | --- |
| 找不到设备 | 点击刷新，检查数据线，并关闭占用串口的工具 |
| 不知道填哪盏灯 | 在 HA 实体设置复制目标灯以 <code>light.</code> 开头的 ID |

## 步骤 2: 配置 E1003 {#configure_panel type=manual required=true config=devices/review_setup.yaml}

点击 **保存配置**，保持通电。

等待“检查设备 → 保存配置 → 重启并验证”完成。保存阶段如显示倒计时，等待其结束；最终以 **配置已保存并验证** 为完成标志。

<details>
<summary>技术详情</summary>
<p>App 自动核对固件项目、版本和硬件，需要时安装预编译固件。只有一个配置入口，不需要用户编译或选择烧录套餐。</p>
<p>参考固件 0.2.1 固定 plaintext-only，App 需要 contract 14；无加密选择或 API 密钥输入/复制。最后写入后至少通电 65 秒，再重启读回。</p>
<p>固件大小 1,337,072 B；SHA-256：<code>23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528</code>。烧录为 115200、offset 0x0、不全片擦除并保留 NVS。实际升级与迁移仍待本版实机验收。</p>
<p>正式候选仍禁用；公开契约为 5，人工审阅步骤不写设备。构建与软件检查已通过，但 0.2.1 最终真机上传尚未开始。正式接入等待公开 contract 14、兼容 App 与固件下载 URL。</p>
</details>

### 故障排查

| 问题 | 处理 |
| --- | --- |
| 配置失败 | 查看当前错误，处理后重试；不要擦 NVS 或删除恢复记录 |
| 仍在保存或验证 | 保持通电，等待最终结果；“正在重启”不是成功 |

## 步骤 3: 完成后验证 {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

仅在 App 显示 **配置已保存并验证** 后继续。

### 故障排查

| 问题 | 处理 |
| --- | --- |
| 灯没有响应 | 检查灯的 ID、调光支持与 HA 动作权限；触摸和真实控灯仍待验收 |
| 屏幕未跟随灯变化 | 动态状态与亮度同步仍需 HA Blueprint 或适配 |

### 部署完成

1. 使用成功页显示的 **设备地址**，在 HA 添加 ESPHome 设备，无需 API 密钥。
2. 允许设备执行 Home Assistant 动作。
3. 测试开关和四档亮度，再关闭 App 复测。只有这五个触摸区有绑定；保存成功不代表真实控灯或屏幕同步已通过。

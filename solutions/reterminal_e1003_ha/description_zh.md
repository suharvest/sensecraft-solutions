# E1003 智能控制面板演示

通过 USB 将 reTerminal E1003 连接至电脑，并一键接入 Home Assistant。本方案自动烧录出厂 ESPHome 固件、部署或检测 Home Assistant 服务，并通过原生 ESPHome 集成将面板自动注册到 Home Assistant 中。

全流程自动化部署，无需手动编译固件或编辑底层 YAML。

## 功能介绍与准备工作

将 E1003 智能触控面板烧录并接入 Home Assistant，用于控制灯光与场景。

开始前请准备：

- 一台 reTerminal E1003 面板及 USB 数据线。
- 运行部署工具的电脑，且局域网内可访问 Home Assistant。
- 用于面板连接的 2.4 GHz Wi-Fi 网络。

## 快速上手

1. 使用 USB 数据线将 E1003 连接至电脑，在部署工具中选择对应串口。
2. 一键安装出厂 ESPHome 固件至 E1003 面板。
3. 部署 Home Assistant（若目标主机已运行 HA 则自动检测跳过）。
4. 输入 E1003 面板 IP 及 Home Assistant 凭据，自动将面板注册至 Home Assistant。
5. 在 Home Assistant 中通过自动化将面板的触控操作绑定到目标灯光实体（`light.*`）。

> **功能说明**：面板固件提供开关与亮度调节触控区域。在 Home Assistant 中，只需创建简单自动化即可将面板的触控动作联动到任意灯光实体。

<details>
<summary>技术详情与验证状态</summary>
<p>参考固件基于 0.2.1，固定使用明文 native API（TCP 6053），不启用 API 加密、无密钥复制，无需 MQTT 或设备 Web 服务，仅支持 USB 更新。</p>
<p>软件构建与界面检查已通过。硬件验收尚未完成。硬件验收需要覆盖 0.2.1 固件上传、五个触摸动作、Home Assistant 状态变化，以及从外部改变灯光后面板显示的更新。墨水屏断电保留画面属于屏幕特性，不代表触摸电路供电正常。</p>
<p>本方案已配置公网 CDN 固件下载，支持通过 USB 一键烧录；正式运行依赖 Home Assistant 网络连通，任意灯具的屏幕状态与亮度同步仍需 Home Assistant Blueprint 或适配器支持。</p>
</details>

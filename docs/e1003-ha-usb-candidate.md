# E1003 参考设计：0.2.1 plaintext-only（实机待验收）

正式 technical 候选保持 `enabled:false`、单一 `usb_candidate` 入口和公开 contract 5 可校验的
人工 review stub。页面入口统一为“配置 E1003”，主操作为“保存配置”；一张表单完成自动检查、按需安装、配置及保存验证。

## 最新设计取代 0.2.0 可选加密

主控报告 0.2.0 在 610 秒免密复查时曾通过，随后设备再次返回
`RequiresEncryptionAPIError`。保留 runtime encryption 能力不能保证参考使用始终免密；
外部客户端可重新配置加密，但此次重新加密的具体来源**尚未确认**，不归因于某个客户端。
一次定时读回通过不能证明持续免密。

最终方向是 **0.2.1 plaintext-only**：彻底移除参考固件 `api.encryption` 的编译能力。
App 移除可选加密 checkbox 和所有 key 复制入口，`encrypt_api` 仅兼容 false 请求，
新契约为 14。开发者入口 `e1003-dashboard.yaml` 独立保留加密，不属于此参考候选。
固件 `09b3bbb` 已提交；App UI 实现为 `475caa01`，原生验收文档为 `f65d0b36`，
构建与软件检查通过；0.2.1 真实设备上传尚未开始，
不能声明新固件已烧录或新 App 的设备流程已通过。

## 资源与提交状态

- [固件 PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2)：`09b3bbb`，
  project `love4yzp.e1003-dashboard`，版本 `0.2.1`，profile `e1003-release.yaml`。
- Factory **1,337,072 bytes**，SHA-256
  `23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528`。
  [manifest](../solutions/reterminal_e1003_ha/assets/firmware/manifest.json) 与模板已同步真实资源，公网 URL 仍为空。
- [App PR #162](https://github.com/suharvest/app_collaboration/pull/162)：代码 `475caa01`，原生验收文档 `f65d0b36`，contract 14。
  加密 checkbox、所有 key 复制入口已删除；`encrypt_api=true` 在硬件访问前被拒绝，旧字段仅接受 false。
- 编译产物：`USE_API_PLAINTEXT` 存在，`USE_API_NOISE` / `USE_PROVISIONING` 不存在。
  这是构建证据，不能替代设备 API 报告 `api_encryption_supported=false` 的实测。

[`stage_e1003_candidate.py`](../scripts/stage_e1003_candidate.py) 用真实 size/SHA 生成禁用的
作者审阅副本；封面引用指向新 `e1003-keyless-cover.png`。它不部署设备，不代表新镜像硬件通过。
用法见[资源说明](../solutions/reterminal_e1003_ha/assets/firmware/README.md)。
115200、offset 0、不全片擦除和 NVS 策略保留；不同构建必须更改 `project.version`，
同步 source/version/size/SHA 和模板校验和，不能只改内容版本。

## 目标交互与执行边界

| 项目 | 0.2.1 / contract 14 方向 |
| --- | --- |
| 用户输入 | USB 端口、`light_entity`、可选 Wi-Fi 名称/密码；无加密或 key 输入/复制控件 |
| API | 参考固件编译为明文 native API（TCP 6053）；`encrypt_api` 仅兼容 false，true 在硬件访问前拒绝 |
| 保存网络 | 已有可用网络时复用；首次联网填写 Wi-Fi。最终硬件流程仍待验证 |
| 自动安装 | 按 canonical manifest 核对 project/version/hardware/name；匹配清单中的 0.2.1 才跳过，安装前校验真实 size/SHA，安装后再查身份 |
| 保存 | 写灯光绑定，通电等待至少 65 秒，再复位免密读回；不以 RAM 读回或 ready 事件当完成 |
| 旧加密设备迁移 | 不套用 0.2.0 的清 key 流程作为已验证结论；等待新固件升级、NVS 与旧记录处理的最终证据 |
| HA | 无 API key 接入；HA 动作权限、真实控灯和屏幕同步独立验收 |

仍只保留一个部署入口，不增加“烧录 / 仅配置”套餐。不在公开 schema 中伪造 contract 14
执行类型或无处理器的表单。未来从 App 真源同步契约并分发兼容 App 后，才接单一原生步骤。

## 页面文案与注意力顺序

方案名缩为“E1003 灯光面板配置演示 / E1003 Light Panel Setup Demo”。首屏只保留
“连接设备，填写要控制的灯。App 会自动检查并按需安装固件。”

- 连接：串口选择与刷新同一行；灯字段手动粘贴 HA 实体设置中的 `light.*`，不声称自动发现。
- 网络：Wi-Fi 说明默认关闭折叠；已有网络可留空，首次或换网填写 2.4 GHz 名称/密码；不声称已探测到网络。
- 保存：短步骤名“配置 E1003”，按钮“保存配置”；查看检查、保存、重启验证三个阶段，成功标志为“配置已保存并验证”。倒计时只引用后端状态，不在内容层造计时器或另一套完成状态。
- 完成：HA 添加 ESPHome、设备地址和动作权限只写入 guide 的 `post_deploy` 内容；App 原生 handler 已实现成功前隐藏，成功后才显示设备地址和 HA 下一步。
- 详情：使用默认关闭的 HTML `details/summary` 收纳版本、SHA、擦除策略和验证状态。仓库 `md_to_html` 及 guide parser 已验证保留这些元素；块内使用原生 HTML，不依赖未启用的 `md_in_html` 扩展。

内容文案已在 `2bd1052` 完成，本轮不重写。App PR #162 的 `475caa01` 已实现上述交互：
USB 刷新复用共享 `pickSerialPort`；顶部 badge 与共享 `deploymentStatus` 使用同一状态源；
保存倒计时恢复后端剩余秒数，零秒不代表成功；保留三个阶段、失败原因和重试。
空日志隐藏，密码提交即清空，成功后 SSID 也清空，避免下次误改网络。
这些是 App 已实现的行为；正式内容仍为人工审阅步骤，不新增公开 schema 不支持的执行字段。

主控提供的无密钥 `ui-implementation-evidence.json` 与原生验收文档
[`f65d0b36`](https://github.com/suharvest/app_collaboration/commit/f65d0b36) 分别记录软件与窗口检查：
Ego 浏览器模拟在阻止真实请求的条件下通过倒计时、失败重试和成功下一步流程，
桌面及 375×812 视口无横向溢出。实际 macOS 原生窗口经 AX 和仅该窗口截图核对，
短标题、同栏 USB 刷新、实体 ID 帮助、默认折叠、无密钥控件、成功前隐藏 HA 内容和空日志均符合要求。
设备已由用户移除，USB 未选；**未点击保存、未创建真实 setup job**。Playwright 文件已更新但未本地运行。
本内容会话只采纳指定公开证据，不操作 App 或设备。

## 触摸、图像与网络

固件只为灯开关及 25/50/75/100 五个触摸区定义动作；其它图形无点击绑定。
触摸坐标不改，仅有 INFO 诊断，触摸/控灯仍待验收，不宣称已修复。
USB Improv、ESPHome native API、同一可达 LAN、无 MQTT/设备 web server 和 USB-only 边界保留。

保留官方实体图和生成架构封面；新生成封面已将 Device key 改为 **No API key**，表达编译设计而非实机已验收。
旧架构图文件作为来源历史保留，不再用作封面或当前 gallery 引用。照片是官方展示界面，不是本固件验收图。
[素材来源](../solutions/reterminal_e1003_ha/gallery/README.md)继续保留，产品族 + `purchase.require`
不变，不绕过 `purchase_profile`。

## 证据与下一步

[检查报告](e1003-ha-usb-checks.md)保留此前 19 固件工具检查及 config/compile 证据，无新 compiler warning。
本轮主控报告 964 前端测试、54 Python + 5 subtests、Black（181 文件）、Ruff、production /
PyInstaller / Tauri 构建通过；lint 为 0 errors / 107 existing warnings。
App 完整 CI 仍需处理已有 Rust 方案快照差异，不能将这些聚焦检查称为完整 CI 全绿。
RAM 112,583 B，app flash 1,271,415 B，factory 比 0.1.0 少 41,440 B。
软件与原生窗口检查不等于最终设备配置提交验收。

此前 WCH 端口消失，**0.2.1 最终真机上传尚未开始**。用户已移除设备并明确排除本轮实体测试，
本轮不等待硬件。不能写已烧录或 `api_encryption_supported=false` 实机通过，也不能从墨水屏
断电留图推断触摸电路有电。五个灯光触摸区、真实 HA 控灯和动态同步仍待确认。

0.1 加密证据、0.2.0 实际升级/免密复位读回/610 秒曾通过及后续再次要求加密的记录均为历史；
发起重新加密的来源未知，不能提升为 0.2.1 验收。新 Wi-Fi 表单、升级和持续免密也仍待实测。
发行仍等待公开 contract 14、兼容 App 与固件下载 URL；本轮不发布。

本内容会话仅复制用户点名的公开 JSON、manifest、新封面及素材说明，真实固件只供既有打包验证；
不枚举其它 `.local-*`，不读取恢复记录，不操作 App/串口或发布二进制。

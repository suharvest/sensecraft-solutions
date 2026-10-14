# reTerminal E1003 HA USB 候选方案与接入契约

本交付属于 AGENTS.md Part F 的内容作者流程。方案位于
[`solutions/reterminal_e1003_ha`](../solutions/reterminal_e1003_ha/solution.yaml)，
保持 `enabled: false`，没有 `verified: [hardware]` 声明。它可做内容校验、资源校验、
生成本地烧录审阅包；尚不能从 App 完成配网、key 和目标写入。
这里的人工步骤只供审阅，不是可执行配置的替代品，不能凭其完成状态放行部署。
后续主会话已在已安装 App 0.7.3 完成独立本地副本的 USB 实机烧录，并由父客户端
验证原 key 与 target 保留，见[检查报告](e1003-ha-usb-checks.md#app-本地实机测试)。

## 固件与资源来源

- [固件 PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2)，
  分支 `feat/e1003-usb-runtime-provisioning`。
- 源码 commit：`981616a9e7bb47398bde63ad283776346f5f57ed`，
  profile：`e1003-release.yaml`，项目：`love4yzp.e1003-dashboard`，版本 `0.1.0`。
- 实际读取了该 commit 工作树的 `e1003-release.yaml`、`tools/provision_device.py`、
  `docs/provisioning.md`、`docs/provisioning-verification.md` 和
  `docs/sensecraft-release-plan.md`。另查了 `packages/ha-bridge.yaml` 的目标文本实体约束。
- factory image 大小 **1,378,512 bytes**，SHA-256：
  `08d616e856cd4d48a0fef0b4e5782e3c4ac1b9efdc1e1647701707bec8bdc540`。
  本轮直接重新计算了真实构建产物的哈希，结果一致。
- 当前没有公开下载 URL。按仓库规则不提交 `.bin`，不创建 release 或 CDN 资源。
  [资源清单](../solutions/reterminal_e1003_ha/assets/firmware/manifest.json)
  中 `download_url` 明确为 `null`。

[`stage_e1003_candidate.py`](../scripts/stage_e1003_candidate.py) 是内容作者工具。
它只接受大小、SHA 完全匹配的 factory image，输出到 Git checkout 外的新目录；
只复制列明的方案文件和该固件，不扫描固件仓库、不复制整个 `.esphome`。
传入路径或其符号链接目标含 `provisioning` / `verification` 时，在读取前拒绝。
它将模板转为 `devices/e1003_usb.yaml`，替换 EN/ZH 的第一个步骤引用，仍保持禁用。
最终用户不运行此工具。可复现命令见
[资源说明](../solutions/reterminal_e1003_ha/assets/firmware/README.md)。

## schema 与执行实现审查

公开契约为 `spec/capabilities.json` 的 **contract_version 5**。`spec/*.json` 为生成文件，
本轮没有手改。另只读审查了本机 `app_collaboration` 的 Python engine 与 frontend，
HEAD `39aee2da23b2604d2d2cde6bcf3c20c0aecbd16f`；所查文件没有未提交改动。
该源码快照不代表用户已安装 App 或独立 `sensecraft-engine` 二进制的能力。
本轮没有启动 engine、连接串口或改动独立项目。

| 能力 | schema / 实际源码证据 | 结论与候选处理 |
| --- | --- | --- |
| USB 烧录 | `FirmwareSource`、`FlashConfig`、`PartitionConfig`；`deployers/esp32_deployer.py` 的 `deploy()` | 可描述实际文件、checksum、chip、baud、offset；本地生成的配置使用现有 `esp32_usb` |
| 固件路径 | `models/device.py:resolve_remote_assets()`、`esp32_deployer.py` 的 partition 候选路径 | source 相对 solution base_path；partition 先尝试 source 目录，再旧目录及 base_path。候选两处均写 solution 相对完整路径，最终能解析到同一文件 |
| 资源完整性 | `services/resource_resolver.py:resolve()`、`_download_and_cache()` | 远程下载分支检查 checksum；本地路径分支只解析路径。本地打包工具先验 hash；正式接入应在每次烧录前再次校验本地实际文件 |
| 全片擦除 | `esp32_deployer.py:full_erase_by_default()`、`deploy()`；`DeviceConfig.get_step_option()` | 默认可能全擦；`steps[id=erase].default: false` 是公开 schema 可表达且实际 deploy() 会读取的覆盖。候选显式设置，不依赖 UI 默认 |
| schema 漂移 | 本机 `FlashConfig.erase_regions` 可改变擦除默认值，但公开 schema 未导出它 | 不把未知字段当安全保障；候选不用它。engine 后续更新该字段时应从真源重新导出 spec |
| 用户输入 | `UserInputConfig`；`deployers/base.py:_build_action_context()` 与 ESP32 deployer 的 actions 调用 | 输入可进入模板上下文，不能自动变成协议写入。ESP32 deployer 没有消费 Wi-Fi/target 的专用操作；候选不放空表单 |
| key 生成 | `UserInputConfig.generate` 只声明 `hex32` | 不能据此声称已生成 ESPHome Noise 所需的 base64 编码 32 字节随机 key；必须由适配器生成并私密保存 |
| 串口向导 | `SerialWizardConfig` 只有 baud、port、welcome、字符串按钮；`deployers/serial_wizard_deployer.py` 只检查配置后返回 ready | 不构成 Improv 配置器 |
| 实际串口传输 | `routers/serial_wizard.py:_reader_loop()` 按 UTF-8 replacement 解码；`send_line` / `action_click` 按 UTF-8 编码并回显 | 二进制帧可能损坏，且敏感数据可能回显；不复用它发送 Wi-Fi/Noise 配置 |
| 原生 API | 在所查 engine 的 `provisioning_station/`、`frontend/src/` 和 `pyproject.toml` 未找到 Improv、`noise_encryption_set_key` 或 `aioesphomeapi` 实现/依赖 | 此快照没有所需配置链路；CLI 二进制能力仍需单独验证，不能由现有 schema 推断 |
| 人工 verify | 公开契约允许 `manual verify=true`；实际 `manual_deployer.py` 不执行设备 I/O 即返回成功 | 可渲染验收清单，不能强制验证；整个候选保持禁用，不能把此步骤当成发布 gate |

### 烧录参数及保存范围

审阅 payload 位于
[`esp32_usb.yaml.in`](../solutions/reterminal_e1003_ha/assets/firmware/esp32_usb.yaml.in)。
ESP32-S3、`dio`、`80m`、`4MB`、`115200`，**merged factory image 写到 `0x0`**。
不把 factory image 写到 `0x10000`，不追加重复的 bootloader / app 写入。
`4MB` 来自真实构建参数；32 MB 是实物容量，不应据此改写分区布局。
WCH 提示为 `1a86:7522`，不使用其他芯片产品的 VID/PID。

本轮从该 factory image 的 `0x8000` 分区表读取到：

| 分区 | Offset | Size |
| --- | --- | --- |
| otadata | `0x9000` | `0x2000` |
| phy_init | `0xb000` | `0x1000` |
| app0 | `0x10000` | `0x1c0000` |
| app1 | `0x1d0000` | `0x1c0000` |
| eeprom | `0x390000` | `0x1000` |
| spiffs | `0x391000` | `0xf000` |
| nvs | `0x3a0000` | `0x60000` |

此 factory image 的写入范围小于 NVS 起点。正常同图像 USB 更新禁用全片擦除，
不能把出厂恢复当作更新。App UI 仍可改步骤选项，正式接入须确保正常更新流程不会
误开擦除，并在验收中检查真实 esptool argv。跨版本迁移、其他 erase policy 不在
固件原有保留配置证据内。

## 最小 engine / App 接入任务

以下均是**待实现契约**，不是当前已支持的 YAML 或 HTTP API；不放入活动方案配置。
建议复用 `esp32_usb`，增加一个明确的 `esphome_provision` 部署类型及 App 配置组件，
而不是让内容脚本承担用户配置。engine owner 应从模型真源导出 schema/capabilities，
增加能力探测，旧版 App/CLI 缺能力时在烧录前拒绝整个流程。

### 输入与实际设备写入映射

| 输入 / 内部值 | 校验与保密 | 必须实现的执行路径 |
| --- | --- | --- |
| USB port | 用户选择；独占串口，不自动抢占其他进程 | 打开 UART0 115200，DTR/RTS 初始关闭；必要时显式 WCH HardReset，等十秒启动；Improv identity RPC 3 |
| Wi-Fi SSID | 1–32 UTF-8 bytes | Improv RPC 1 的第一个字符串 |
| Wi-Fi password | 空表示开放网络；否则 8–63 UTF-8 bytes；仅内存，不写部署参数历史/日志 | Improv RPC 1 的第二个字符串；解析返回 IP，再连 TCP 6053 |
| device identity | project 精确匹配，name 匹配 `reterminal-e1003-[0-9a-f]{6}`；API 再查 MAC | 串口身份与 API device_info 对照；已有恢复记录时 MAC 必须相同 |
| API key | OS CSPRNG 32 bytes，base64；拒绝全零；每设备独立 | 初始零 PSK 仅用于未配置设备的 Noise provisioning handshake；确认可 provision 后调用 `noise_encryption_set_key`；随后用真实 key 加密重连 |
| light target | `^light\.[a-z0-9_]+$`，总长 ≤63；不要求 HA 登录/枚举 | `list_entities_services` 发现唯一 TextInfo `Main light target`（允许设备名称前缀），按原生实体 key 发 `text_command`，订阅 TextState 读回同值 |
| IP override | 仅连通性兜底；不能替代身份检查 | mDNS 不通时用 Improv 返回 IP；仍核对 project/name/MAC，不访问其 URL |
| HA confirmation / action permission | 用户到 HA 界面确认；App 单独记录为待确认 | 真实 HA 集成、加密连接、触摸灯光测试，不以烧录完成代替 |

可参考固件 PR 中 `provision_device.py` 的 wire client 和公开 tests；不要复制私有记录，
也不要把维护者脚本作为 App 运行依赖。Python App 可封装最小逻辑并随应用打包
`aioesphomeapi` 兼容版本；独立 CLI 需等效实现或明确返回缺能力，不启动用户编译工具。

### 传输与恢复必须保留的行为

1. **Improv 二进制流：** UART0 同时有日志。保留分片缓冲、匹配 `IMPROV`/版本/外层长度，
   严格校验 checksum，跳过日志。每个请求末尾加 newline，避免下一帧丢 header。
   RPC 响应仅额外接受已捕获的「内层数据长度之外单个零 footer」格式；不能宽松忽略
   任意尾随字节。UTF-8 校验按字节计算长度。设备返回的 URL 仅提取地址，不代表 web server。
2. **私有恢复：** 安装 key 前原子保存设备身份、key、MAC、状态和地址；POSIX 0600，
   Windows 使用仅当前用户可读 ACL / 系统凭据存储。不要把 key 写进普通 `user_inputs`、
   device_connections、zip、导出配置、错误日志。进程崩溃或响应丢失后先用同一记录重连，
   不能生成第二个 key。key 丢失时停止，明确授权后才能走破坏性的恢复流程。
3. **激活过渡：** 固件 key 激活延迟 100 ms；允许加密重连约 200 ms 间隔的有限重试，
   参考已验证客户端的最多四次。不要因短断线重复发送 set-key 请求。key 激活后零 key 必须拒绝。
4. **保存与断电：** Wi-Fi/key 的 handler 立即同步；runtime text 默认 60 秒 flush。
   目标读回只证明 RAM。最后一次写入后保持供电至少 65 秒，UI 显示保存中；之后复位并
   加密重连、再次读回才能声明该次配置持久化。中断要恢复未完成状态，不能提前显示可拔线。
5. **更新与恢复：** 正常 USB 更新保留 NVS，不全片擦除。首次写入不熟悉的旧固件/分区时
   先判断兼容性，不自动清除。丢 key 的恢复是独立、需明确确认的破坏性路径。
   此 profile 无 OTA listener；禁止为绕过 runtime key schema 而开启无鉴权 OTA。

### 调用与状态接口建议

最小内部接口可为 `provision(port, ssid, password, target, recovery_ref?, host_override?)`，
返回 identity、host、私有 `credential_ref` 和各阶段证据，**不返回日志可见的原始 key**。
API key 只通过明确的本机私密 reveal/copy 操作交给用户填入 HA。
同一设备重复调用须复用 recovery_ref；失败返回可恢复状态和脱敏错误。

复用现有 deployment status/progress/logs 通道，阶段按顺序为：
`identity_checked → wifi_connected → recovery_saved → key_installed → encrypted_verified
→ target_readback → saving → persisted_verified → ha_confirmation_required`。
App 可以在已有部署页面承载配置组件，不需要为此新建一组通用串口 API。
持久化验证失败、用户未确认 HA、Blueprint 尚未接入时，不能给整体部署成功。
失败/取消须保留安全恢复记录；串口锁在结束后释放，不能调用自动抢占端口操作。

### 最小补丁拆分与完成证据

| 接入任务 | 最小改动范围 | 完成证据 |
| --- | --- | --- |
| 能力与输入契约 | engine 模型、注册表、能力探测、生成 spec | 不支持的 engine 在烧录前拒绝；每个输入有上述写入映射 |
| 配置执行器 | Improv parser/transport、native API client、私有恢复存储 | 碎帧/日志/坏 checksum/footer/newline、丢 key 响应、100 ms 激活重试、身份不符及零 key 拒绝测试 |
| App 组件 | 端口选择、内存密码表单、保存倒计时、私密 key 复制、失败续接 | 不要求用户装 Python/ESPHome、编译或运行维护者脚本 |
| 烧录防护 | 实际文件 SHA、擦除策略、端口独占 | 错误文件触碰设备前失败；正常更新无 erase_flash；NVS 不在写入范围 |
| HA 适配 | 动态目标 Blueprint/等效适配，HA 导入/选择实体引导 | 目标 A→B 后控制和状态均跟随 B，A 不再驱动；亮度变化、重启、重连、不可用目标测试 |
| 整体验收 | 两台同硬件/布局设备、相同 SHA、独立 Wi-Fi/key/target | App 关闭后独立运行；支持的 Windows/macOS 安装与实际 App 部署，另记录中国大陆资源下载验证 |

## 证据边界与当前检查

固件公开验证记录报告：11 项软件测试；一台 E1003 的 USB/Improv 配网、独立 key
激活/加密重连、零 key 拒绝、目标写入读回、等待保存后两次复位，以及同图像同分区 USB
覆盖更新后保留配置。这些证据属于固件维护者流程；测试目标并非真实 HA 灯。
`docs/provisioning.md` 仍有「USB 更新未验证」旧措辞，本候选采用较新的公开验证记录及
release plan，但仅据此声明同图像、同分区已验证。

本轮没有读取 `.esphome/provisioning/`、`.esphome/verification/`，没有读取实际 key、
NVS/flash 备份或私密日志，没有使用 `/dev/cu.wchusbserial2120`。
本轮新增的候选检查记录在 [检查报告](e1003-ha-usb-checks.md)。

用户 App 0.7.3 已在 `127.0.0.1:20116` 导入独立测试副本并完成真实 USB 烧录。
部署 `d9140919-7b3e-4b38-83a0-f23daa1322d2` 用时 80.704458 秒，写入哈希校验通过，
擦除未触及 NVS；父客户端随后使用原 key 加密重连并读回原 target。
详情及公开证据见[检查报告](e1003-ha-usb-checks.md)。
这不代表 App 已具备配网、key 或目标配置表单，真实 HA 控灯和动态显示同步仍待验收。
正式公开资源、engine 配置接入和剩余整体验收完成前，正式候选保持禁用。

## 部署页注意力与参数布局

用户可见标签统一为 **按钮控制的灯**。这是灯光卡片的一项绑定，开关及四档亮度
共用同一个灯实体；面板还包含时钟与温湿度卡片。只改标签，不改 `target`、
`cfg_target_main_light`、`Main light target` 等协议或固件标识。

### 当前联调顺序

| 阶段 | 此刻只看什么 | 完成信号 | 留到后面 |
| --- | --- | --- | --- |
| 安装面板程序 | USB 端口、安装动作 | 写入校验通过 | Wi-Fi、灯的 ID、连接密钥 |
| 联网并设置按钮 | Wi-Fi 名称、密码、按钮控制的灯 | 加密重连与读回一致；通电 65 秒后复位仍保留 | HA 动作权限 |
| 在 Home Assistant 启用控制 | 设备确认、连接密钥、动作权限 | 开关与四档亮度实际控制同一盏灯 | 显示同步单独验收 |

开始前只准备好灯的实体 ID。当前 App 只执行安装；第二阶段由联调客户端执行，
表中参数不表示当前已有 App 表单。时钟或温湿度正常显示不能证明按钮绑定成功。

### 字段排版与单行用词

以下是后续配置表单的设计约定，**尚未实现**。采用单列，按「连接网络」和
「设置灯光按钮」分组。每个字段独占一行，标签在上、辅助说明在下；
输入框留足完整实体 ID 的宽度，不把多个技术名词塞在同一行。

| 原词 | 主标签 | 一行辅助说明 / 出现位置 |
| --- | --- | --- |
| SSID | Wi-Fi 名称 | 面板要连接的网络 |
| password | Wi-Fi 密码 | 该网络的连接密码；默认遮蔽 |
| 目标灯 entity_id | 按钮控制的灯 | 从 HA 复制灯的实体 ID，如 `light.bedroom`；开关和四档亮度共用此灯 |
| API key | 设备连接密钥 | 首次自动生成、后续复用；只在 HA 接入阶段提供明确的复制操作 |
| flash | 安装面板程序 | 写入预编译程序，无需编译 |
| erase=false | 不全片擦除 | 固定安全选项，不作为普通必填项；不等于完全不擦写扇区 |

115200、offset 0、4 MB 布局留在高级说明中。当前 App 按钮仍由 engine 渲染，
内容修改不会自行改变该按钮或新增表单；未来主操作建议为「安装并设置」。

### 从配置到安装

未来可先收集三项输入，准备态显示 **设置已准备，尚未写入面板**。这些输入不参与
编译，Wi-Fi 密码只保留在本次会话内。点击「安装并设置」后，依次显示
**正在安装程序 → 正在联网并设置按钮 → 正在保存设置，请保持通电**。
最后一次写入后等待至少 65 秒并复位验证，再引导到 HA；不能在安装完成时直接
宣告整个方案成功。此自动衔接仍需 engine 配置执行器，不增加空 `user_inputs`。

本节来自两轮指定角色讨论：文案角色 `6bf9a301-244b-4001-94d3-d77236908b60`
（会话 `0669726b-d5b3-4e95-8504-6fe0c2de8d12`）与高级工程师
`0420b51f-e06e-413e-9416-befeb061f0a8`（会话 `fe1b9d7f-fa72-4e69-a073-f5605a39c753`）。
未采用「刷入即用」、用屏幕显示代替绑定验证、或把「不全片擦除」简写成「不擦除」的表述。

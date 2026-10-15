# E1003 统一部署技术演示

本交付属于内容作者流程，分类为 `technical`。候选位于
[`solutions/reterminal_e1003_ha`](../solutions/reterminal_e1003_ha/solution.yaml)，
保持 `enabled: false`，未声明整体验收通过。演示同一固件安装后，如何按设备配置网络、
独立连接密钥和灯光按钮绑定；真实 HA 控灯和动态屏幕同步不属于已验证结果。

当前交互为**一个部署入口、一张表单、一个任务**：用户选择串口、填写灯与网络设置，
点击“部署并保存配置”。App 根据方案清单自动核对固件身份，匹配则跳过烧录，需要时
校验并安装预编译镜像，再写入配置、等待 65 秒、复位及加密读回。无需用户判断是否烧录。

主控已完成打包后端与共享前端的统一任务：匹配后跳过烧录、保存 65 秒、复位并加密读回。
另一次受控安装仅将首次探测故障注入为无响应，随后真实写入、校验并验证原 key/绑定保留。
这不是出厂空白设备或新 Wi-Fi 表单验收。此前原生窗口、密钥复制及介绍显示证据保留；
详情见[检查报告](e1003-ha-usb-checks.md)。

## 封面与产品实物图

封面使用生成的架构示意；图库与双语正文引用 E1003 官方实物照片。照片中的官方展示界面
不是本固件验收画面，架构图也不是实际 App 截图；HA 控灯与状态同步待验收。
素材来源和生成提示见[图库说明](../solutions/reterminal_e1003_ha/gallery/README.md)。
本地素材随内容导出及作者审阅打包保留；未上传 CDN。`device_catalog` 仍只声明产品族与
`purchase.require`，不硬编码 SKU 图片或购买地址，不绕过运行时 `purchase_profile`。

## 固件与资源来源

- [固件 PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2)，
  分支 `feat/e1003-usb-runtime-provisioning`。
- 镜像构建源码：`981616a9e7bb47398bde63ad283776346f5f57ed`；
  profile `e1003-release.yaml`，项目 `love4yzp.e1003-dashboard`，版本 `0.1.0`。
- factory image：**1,378,512 bytes**；SHA-256
  `08d616e856cd4d48a0fef0b4e5782e3c4ac1b9efdc1e1647701707bec8bdc540`。
  后续配置客户端变更没有重编译此镜像。
- 没有公开下载 URL。[资源清单](../solutions/reterminal_e1003_ha/assets/firmware/manifest.json)
  的 `download_url` 为 `null`，Git 中不包含 `.bin`。

[`stage_e1003_candidate.py`](../scripts/stage_e1003_candidate.py) 是作者侧审阅工具，
只接受大小与 SHA 匹配的镜像，按白名单复制内容到 checkout 外的新目录，物化
`esp32_usb` 配置并保持禁用。不扫描私密目录，不连接设备，不配置或发布。
最终用户不运行此工具；命令见[资源说明](../solutions/reterminal_e1003_ha/assets/firmware/README.md)。

## App 原生能力与公开契约

当前公开 `spec/capabilities.json` 为 **contract 5**，统一部署新增契约为 **contract 12**。
公开 schema 尚不支持 `e1003_config`；本 PR 不手改生成的 spec，也不将未知类型塞进
执行 YAML。正式 guide 保留三个人工审阅步骤，最后一个为 `verify=true`；
人工步骤返回成功不能证明设备配置或真实控灯通过。

App 工作基线为主线 `50fc49df`，其上新增原生实现；这不是该基线已发布此功能的声明。
统一部署已推送 [App 草稿 PR #162](https://github.com/suharvest/app_collaboration/pull/162)，
标题为 `feat: deploy E1003 in-App with automatic firmware checks`，commit `689789d9`，contract 12。
`6efdf2ee` 仅对应此前 contract 11 窗口证据；新提交不代表已合并或分发。
本内容会话只读核对以下源码及公开文档，没有修改独立 App 仓库：

| 材料 | 已实现行为 |
| --- | --- |
| `docs/e1003-desktop-configuration.md` | 原生配置的作者契约、用户流程与恢复约束；原 contract 11 阶段的材料 |
| `provisioning_station/deployers/e1003_config_deployer.py` | 注册交互步骤，renderer 为 `e1003-config`；deployer 的 ready 结果只代表表单就绪 |
| `frontend/src/pages/deploy/e1003-config-handler.js` | 同一表单提交端口、灯、Wi-Fi 和 `solution_id`，轮询完整任务，成功后显式复制密钥 |
| `provisioning_station/routers/e1003_setup.py` | 创建/查询配置任务；独立的显式密钥复制请求，响应 `Cache-Control: no-store` |
| `provisioning_station/services/e1003_setup.py` | 根据 `solution_id` 加载已启用方案，先执行固件检查/按需安装，再配置及持久化验证；端口租约覆盖完整任务 |
| `provisioning_station/services/e1003_firmware.py` | 读取方案 canonical manifest，核对 Improv 身份、安装前校验镜像、使用捆绑 esptool 写入并校验，再查身份 |
| `provisioning_station/services/e1003_transport.py` | 内建配置传输与私有恢复记录，不运行内容包中的脚本 |
| `docs/reports/e1003-desktop-configuration.md` | 打包后端硬件验证、共享前端检查及原生桌面启动的分层证据 |

同步后的接入任务：完成 App 统一任务的审查与兼容分发，由 App 真源导出并同步
contract 12 的 schema/capabilities，再将人工审阅阶段替换成**单一原生部署入口**。
不再添加“烧录并配置 / 仅配置”套餐，也不把单独 `esp32_usb` 暴露为用户必须选择的路径。
App 统一任务内部复用捆绑 esptool。`e1003_config` ready 只代表表单就绪，完成信号必须来自
整项任务的复位与加密读回；最终 HA 人工验证仍独立保留。

### 自动判定与版本约束

前端传 `solution_id`；后端从方案目录读取 `assets/firmware/manifest.json`，不接受用户任意
指定镜像路径或版本。本轮不改清单既有字段、固件版本、大小或 SHA。

| 判定 / 阶段 | 行为 |
| --- | --- |
| USB Improv 身份 | project 为 `love4yzp.e1003-dashboard`、version 为清单 `0.1.0`、hardware 为 `ESP32-S3`，name 匹配 `reterminal-e1003-[0-9a-f]{6}`；四项均符合才跳过烧录 |
| 串口不可访问 / 明确硬件不符 | 停止，不解释为允许安装 |
| 固件不匹配或可访问设备无有效 Improv 响应 | 进入按需安装；先校验清单、镜像 size 与 SHA-256，再经已捆绑 esptool 写入 `0x0` 并执行 `verify_flash`；不全片擦除，NVS 保留 |
| 安装后身份 | 重新探测 project、version、hardware、name；未匹配则停止，不继续配置 |
| 配置 | 同一任务内完成联网/绑定/独立 key、65 秒保存、复位与加密读回；端口租约覆盖所有阶段 |

跳过分支依据设备报告的项目和版本，不读取整片 flash 比较镜像 SHA。
因此未来不同构建必须使用不同的固件 `project.version`，同步 manifest 的 `firmware_version`、
镜像大小和 SHA；禁止同一 project/version 对应不同构建。它不同于内容 `solution.yaml.version`。
当前 `0.1.0` 只指向已锁定的这份镜像。

### 已有类型的审查结论

| 类型 / 字段 | 结论 |
| --- | --- |
| `esp32_usb` | 已有真实烧录路径；相对固件路径和 checksum 可表达，显式设置 `erase.default: false` |
| `user_inputs` | 单独添加输入不执行设备写入；通用 `generate: hex32` 不能代替 ESPHome Noise key 生成 |
| `serial_wizard` | 旧实现按文本收发，不能承担混有 UART 日志的 Improv 二进制协议 |
| `script.start_command.env` | 早期 local-only 适配已实机通过；installed App 0.7.3 丢弃输入，源码 `39aee2d` 修复。现行引导改用原生表单，不再要求外部服务、venv 或复制脚本路径 |
| `manual verify=true` | 仅供清单与审阅，不执行设备 I/O；候选禁用状态继续保留 |

原生配置不依赖在本候选中新增通用 `user_inputs`。早期 script 字段使用 `light_entity`
避开 engine 的部署 selector 保留键 `target`；App 新表单同样使用 `light_entity`，
固件内部 `cfg_target_main_light` / `Main light target` 不改名。

### 烧录参数及保存范围

审阅 payload 位于
[`esp32_usb.yaml.in`](../solutions/reterminal_e1003_ha/assets/firmware/esp32_usb.yaml.in)。
ESP32-S3、`dio`、`80m`、`4MB`、`115200`，**merged factory image 写到 `0x0`**。
不把 factory image 写到 `0x10000`，不追加重复的 bootloader / app 写入。
`4MB` 来自真实构建参数；32 MB 是实物容量，不应据此改写分区布局。
WCH 提示为 `1a86:7522`，不使用其他芯片产品的 VID/PID。

初始资源审查从该 factory image 的 `0x8000` 分区表读取到：

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
不能把出厂恢复当作更新。早期 `esp32_usb` 可修改步骤选项；新统一安装任务固定不全片擦除，
受控实机安装已使用 PyInstaller 同路 esptool Python API 写入和 `verify_flash`，
随后验证原 key/绑定保留。跨版本迁移、出厂空白设备及其他 erase policy 不在
固件原有保留配置证据内。

## 输入与保存契约

### 输入与实际设备写入映射

| 输入 / 内部值 | 校验与保密 | 执行映射 |
| --- | --- | --- |
| USB port | 用户选择；独占串口，不自动抢占其他进程 | 打开 UART0 115200，DTR/RTS 初始关闭；必要时显式 WCH HardReset，等十秒启动；Improv identity RPC 3 |
| Wi-Fi SSID | 1–32 UTF-8 bytes | Improv RPC 1 的第一个字符串 |
| Wi-Fi password | 空表示开放网络；否则 8–63 UTF-8 bytes；不进 argv 或生成配置文件，发行时仍须确认日志/持久化脱敏 | Improv RPC 1 的第二个字符串；解析返回 IP，再连 TCP 6053 |
| device identity | project 精确匹配，name 匹配 `reterminal-e1003-[0-9a-f]{6}`；API 再查 MAC | 串口身份与 API device_info 对照；已有恢复记录时 MAC 必须相同 |
| API key | OS CSPRNG 32 bytes，base64；拒绝全零；每设备独立 | 初始零 PSK 仅用于未配置设备的 Noise provisioning handshake；确认可 provision 后调用 `noise_encryption_set_key`；随后用真实 key 加密重连 |
| light target | `^light\.[a-z0-9_]+$`，总长 ≤63；不要求 HA 登录/枚举 | `list_entities_services` 发现唯一 TextInfo `Main light target`（允许设备名称前缀），按原生实体 key 发 `text_command`，订阅 TextState 读回同值 |
| 地址选择（内部） | 非表单输入；不能替代身份检查 | mDNS 不通时用 Improv 返回 IP；仍核对 project/name/MAC，不访问其 URL |
| HA confirmation / action permission | 用户到 HA 界面另行确认 | 真实 HA 集成、加密连接、触摸灯光测试，不以烧录完成代替 |

### 传输与恢复约束

- UART0 混有日志：缓冲分片，匹配 Improv header/长度并校验 checksum；请求末尾加 newline。
  RPC response 仅额外接受内层长度之外单个零 footer，不忽略任意尾随字节。
- WCH 重新打开串口需显式 reset 并等待启动；配置任务全程持有串口租约，不抢占其他会话。
- 安装 key 前原子保存私有恢复记录；失败重试复用同一 key。Unix 新记录为 0600、目录 0700；
  Windows 继承 App 数据目录 ACL。正常状态、历史及日志不返回 key，Wi-Fi 密码不写入恢复记录。
- key 激活延迟 100 ms，允许有限加密重连重试。零 key 仅用于未配置设备的初始 provisioning，
  已配置设备不得通用降级。缺失旧记录时停止，不自动清 NVS；跨电脑不是自动恢复流程。
- runtime text 默认 60 秒 flush，RAM 读回不能证明保存。最后写入后通电至少 65 秒，
  再复位、加密重连及读回一致，才报告保存成功。
- 同图像、同分区 USB 更新保留 NVS；跨版本迁移另行验收。当前无 OTA listener，不启用无鉴权 OTA。

任务使用 `POST /api/e1003-setup/jobs` 创建、`GET /api/e1003-setup/jobs/{job_id}` 查询；
显式复制使用 `POST /api/e1003-setup/devices/{name}/key`。这些是 App 路由，不是设备 web server。
导航恢复只保存公开 job ID，不能重复写设备；取消/离开页面不得在硬件工作结束前释放串口。

## 部署页注意力与参数布局

先说明测试目的和验收边界，再按 **同一表单填写 → 自动检查/按需安装/保存 → HA 验证** 展示。
检查、安装和配置是一项连续任务；显示是否跳过、当前进度与复位后读回结果，最后另验真实灯具响应。
屏幕时钟和温湿度显示不能代替绑定或控灯验收。

| 项目 | 页面用词 / 行为 |
| --- | --- |
| 灯光字段 | **按钮控制的灯**；下一行说明“从 HA 复制实体 ID，如 `light.bedroom`”；开关与四档亮度共用 |
| 连接字段 | USB 端口独占一行；Wi-Fi 名称和密码分别一行，密码遮蔽；首次联网必填，已有记录且已联网时可留空 |
| 主操作 | **部署并保存配置**；检查、安装、保存与复位时显示连续进度，不提前提示拔线 |
| 连接密钥 | 自动生成或复用，不混入必填项；成功后点击复制按钮，供 HA 接入 |
| 烧录参数 | 115200、offset 0、不全片擦除留在高级说明，不让用户重复填写 |

统一提交已有匹配跳过后完整保存验证，受控安装分支也已实际写入并验证保留；
两种测试条件分别记录，不扩大为出厂空白设备、新 Wi-Fi 或真实 HA 控灯通过。
文案沿用已完成的 GPD 润色角色与高级工程师讨论，并按原生 App 新证据更新。
App 当前中文字段仍标为“目标灯 entity_id”，英文为“Light entity ID”；内容统一用
“按钮控制的灯”解释用途，建议主控在 App PR 中同步标签与一行辅助说明，不在本仓库改 App 源码。

## 启用前依赖与验收

| 项目 | 当前状态 / 后续任务 |
| --- | --- |
| App PR 与安装包 | [App 草稿 PR #162](https://github.com/suharvest/app_collaboration/pull/162) 已推送 `689789d9`、contract 12；PyInstaller/Rust/Tauri 构建通过，兼容功能待审查和正式分发 |
| 统一任务验收 | 匹配跳过后的完整配置持久化通过；首次 probe 故障注入的真实安装及原配置保留通过；出厂空白设备未覆盖 |
| 公开契约 | 本仓库仍为 contract 5；从 App 真源同步 contract 12 后才替换人工审阅阶段 |
| 固件资源 | 已有真实镜像与 SHA，缺公开下载地址；发布另行授权，不在本任务执行 |
| 新 Wi-Fi | 旧 Improv 配网证据存在；通过新原生表单配置新网络尚未物理验收 |
| HA 与显示 | 设备确认、动作权限、真实灯具响应、触摸仍待验证；动态状态与亮度同步还需 Blueprint/适配 |
| 扩展验收 | 出厂空白设备、两面板隔离、支持平台安装、下载哈希与跨版本迁移尚待覆盖 |

历史 App 烧录和 script 表单的脱敏证据，以及原生表单本轮证据见[检查报告](e1003-ha-usb-checks.md)。
本次内容修改不操作 App 或串口，不读取私有运行目录、key、NVS、flash 备份或设备日志；
不提交本机绝对路径、固件二进制、独立 engine 源码或生成的发布清单。

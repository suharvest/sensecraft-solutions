# E1003 预编译固件与运行时配置技术演示

本交付属于内容作者流程，分类为 `technical`。候选位于
[`solutions/reterminal_e1003_ha`](../solutions/reterminal_e1003_ha/solution.yaml)，
保持 `enabled: false`，未声明整体验收通过。演示同一固件安装后，如何按设备配置网络、
独立连接密钥和灯光按钮绑定；真实 HA 控灯和动态屏幕同步不属于已验证结果。

当前配置路径是**桌面 App 内置 E1003 表单**：内建 Improv / aioesphomeapi 后端完成写入、
65 秒保存等待、复位及加密读回，成功后在 App 内点击按钮复制密钥。
无需外部网页、本机脚本路径或用户安装 Python。打包后端与共享前端已通过单机保存验证；
本地 Tauri App 已启动并加载原生步骤。证据范围见[检查报告](e1003-ha-usb-checks.md)。

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

当前公开 `spec/capabilities.json` 为 **contract 5**，App 新功能导出 **contract 11**。
公开 schema 尚不支持 `e1003_config`；本 PR 不手改生成的 spec，也不将未知类型塞进
执行 YAML。正式 guide 保留三个人工审阅步骤，最后一个为 `verify=true`；
人工步骤返回成功不能证明设备配置或真实控灯通过。

App 工作基线为主线 `50fc49df`，其上新增原生实现；这不是该基线已发布此功能的声明。
App PR 由主控会话创建，链接待补充，不猜测 PR 编号。
本内容会话只读核对以下源码及公开文档，没有修改独立 App 仓库：

| 材料 | 已实现行为 |
| --- | --- |
| `docs/e1003-desktop-configuration.md` | 原生步骤的作者契约、用户流程及恢复约束；要求 contract 11 |
| `provisioning_station/deployers/e1003_config_deployer.py` | 注册交互步骤，renderer 为 `e1003-config`；deployer 的 ready 结果只代表表单就绪 |
| `frontend/src/pages/deploy/e1003-config-handler.js` | App 内填写端口、灯和 Wi-Fi，提交任务、轮询保存状态、成功后点击复制密钥 |
| `provisioning_station/routers/e1003_setup.py` | 创建/查询配置任务；独立的显式密钥复制请求，响应 `Cache-Control: no-store` |
| `provisioning_station/services/e1003_setup.py` / `e1003_transport.py` | 内建配置与传输，不运行内容包中的脚本；私有恢复记录位于 App 数据目录 |
| `docs/reports/e1003-desktop-configuration.md` | 打包后端硬件验证、共享前端检查及原生桌面启动的分层证据 |

同步后的接入任务：由 App 真源重新导出并同步公开 schema/capabilities，确认兼容 App
可分发，再将配置步骤由人工 stub 换成 `e1003_config`。先安装仍复用 `esp32_usb`；
已安装设备可只执行配置。不要把 `e1003_config` 的 ready 事件当作保存成功，必须等待
配置任务完成复位和加密读回。最终 HA 人工验证独立保留。

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
不能把出厂恢复当作更新。App UI 仍可改步骤选项，正式接入须确保正常更新流程不会
误开擦除，并在验收中检查真实 esptool argv。跨版本迁移、其他 erase policy 不在
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

先说明测试目的和验收边界，再按 **安装 → 保存配置 → HA 验证** 展示。
每段只突出一个完成条件：烧录校验通过、复位后加密读回一致、真实灯具响应。
屏幕时钟和温湿度显示不能代替绑定或控灯验收。

| 项目 | 页面用词 / 行为 |
| --- | --- |
| 灯光字段 | **按钮控制的灯**；下一行说明“从 HA 复制实体 ID，如 `light.bedroom`”；开关与四档亮度共用 |
| 连接字段 | USB 端口独占一行；Wi-Fi 名称和密码分别一行，密码遮蔽；首次联网必填，已有记录且已联网时可留空 |
| 主操作 | **保存设备配置**；等待保存与复位时持续显示进度，不提前提示拔线 |
| 连接密钥 | 自动生成或复用，不混入必填项；成功后点击复制按钮，供 HA 接入 |
| 烧录参数 | 115200、offset 0、不全片擦除留在高级说明，不让用户重复填写 |

“安装前收集配置草稿”与“一次连续提交安装和配置”没有在本轮验收，不写成现有能力。
文案沿用已完成的 GPD 润色角色与高级工程师讨论，并按原生 App 新证据更新。
App 当前中文字段仍标为“目标灯 entity_id”，英文为“Light entity ID”；内容统一用
“按钮控制的灯”解释用途，建议主控在 App PR 中同步标签与一行辅助说明，不在本仓库改 App 源码。

## 启用前依赖与验收

| 项目 | 当前状态 / 后续任务 |
| --- | --- |
| App PR 与安装包 | 内建后端已打包并实机通过，Tauri 本地测试 App 已启动；App PR 链接待主控补充，兼容功能尚待正式分发 |
| 公开契约 | 本仓库仍为 contract 5；从 App 真源同步 contract 11 后才替换人工配置步骤 |
| 固件资源 | 已有真实镜像与 SHA，缺公开下载地址；发布另行授权，不在本任务执行 |
| 新 Wi-Fi | 旧 Improv 配网证据存在；通过新原生表单配置新网络尚未物理验收 |
| HA 与显示 | 设备确认、动作权限、真实灯具响应、触摸仍待验证；动态状态与亮度同步还需 Blueprint/适配 |
| 扩展验收 | 两面板隔离、支持平台安装、下载哈希与跨版本迁移尚待覆盖 |

历史 App 烧录和 script 表单的脱敏证据，以及原生表单本轮证据见[检查报告](e1003-ha-usb-checks.md)。
本次内容修改不操作 App 或串口，不读取私有运行目录、key、NVS、flash 备份或设备日志；
不提交本机绝对路径、固件二进制、独立 engine 源码或生成的发布清单。

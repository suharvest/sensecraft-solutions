# E1003 运行时配置技术演示检查报告

日期：2026-10-15。结论：**分类已改为 technical；App USB 烧录和内置表单保存均有实机证据。正式候选仍禁用，公开契约同步、固件资源与 HA 验收待完成。**
接入条件见[技术演示与接入契约](e1003-ha-usb-candidate.md)。

## 当前方向：0.2.1 plaintext-only / contract 14（待验证）

主控补充的观察覆盖此前“十分钟复查未完成”的状态：**0.2.0 的 610 秒免密复查曾通过，
随后又返回 `RequiresEncryptionAPIError`**。重新配置加密的具体来源尚未确认；不能把
一次定时通过或原先清 key 成功当作参考设计能持续免密的证据。

因此 0.2.0 可选 runtime encryption 不再是最终设计。目标 0.2.1 从参考固件彻底移除
`api.encryption` 编译能力，App 移除 encryption checkbox 与所有 key 复制入口；
`encrypt_api` 仅兼容 false 请求，contract 14。独立开发者入口 `e1003-dashboard.yaml` 保留加密。

| 状态 | 结论 |
| --- | --- |
| 新构建/实机 | 主控正在编译验证；0.2.1 的 commit、size、SHA、升级与持续免密结果尚未提供，不猜值或读未授权文件 |
| 新 App | 控件移除和新契约按最终方向更新文案，不声明原生窗口提交或完整新流程已验收 |
| 已知资源 | manifest 和模板仍记录旧 0.2.0，保持其真实 size/SHA；不把旧镜像称作新 plaintext-only 资源 |
| 正式候选 | 单一入口、`enabled:false`、public contract 5 review stub；发行待公开 contract 14、兼容 App 和最终固件资源 |
| 其它边界 | 触摸、真实 HA 控灯/屏幕同步、新 Wi-Fi 表单及迁移细节仍待验收 |

本节依据主控的公开补充，没有读取新的 `.local-*` 文件、设备日志、私有记录或固件。
以下 0.2.0 JSON/测试结果保留为当时的历史快照，不能据此继续给出可选加密为最终默认的结论。

## 历史过渡：0.2.0 可选加密（contract 13）

固件 [PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2) 为
`a7116ee153158505faeec225d691c0cdef85a6da`；App [PR #162](https://github.com/suharvest/app_collaboration/pull/162)
为 `68328f90`、contract 13。`encrypt_api=false` 为默认，开启加密才提供完成后的密钥复制。

| 检查 | 当前证据与边界 |
| --- | --- |
| 固件资源 | 0.2.0；factory 1,377,472 B；SHA `45cbf1ec46d5a00e8362e6d920cd9318841c58f2a081cfae809d9e38e64ccebb`；manifest 和模板同步，无公网 URL |
| 实际升级 | 任务 `56899ea5f4c441aab0bf1ea227c50473` 检测 0.1.0，真实安装 0.2.0；写入校验和身份校验通过，本次无 probe 故障注入 |
| 默认配置 | Wi-Fi 留空复用；旧恢复 key 授权清除加密、写同一 target、等待 65 秒、复位免密读回；`encrypted=false`，记录不含 `api_key` |
| 记录边界 | 无 key 设备可在没有本机旧记录时复用网络；旧加密设备仍用原 key 授权清除，免密重连前不删记录 key，不擦 NVS。无本机记录的复用路径有工具测试，不与本次旧 key 迁移混为同一硬件起始状态 |
| 操作面 | 打包后端 + 桌面共享前端经 browser QA 提交，不是本次 native-window 提交验收；原生实际窗口只确认 checkbox AXValue=0、无 key 复制按钮 |
| 视口 | 桌面和 375×812 截图审查无横向溢出；不把截图审查当硬件触摸证明 |
| 软件检查 | 19 固件工具检查、54 App 聚焦检查 + 5 subtests、956 前端通过；config/compile 通过，无新增 compiler warning |
| 构建体积 | RAM 112,639 B，app flash 1,311,819 B；factory 相比 0.1.0 少 1,040 B |
| API 生命周期 | 移除 10 分钟初始 provisioning timer，关闭等待 API 客户端的 reboot；该轮尚未复查；后续 610 秒读回曾通过，随后再次要求加密，见当前方向说明 |
| 触摸 | 灯开关和 25/50/75/100 五个触摸区，其它图形无点击绑定；坐标未改，只新增 INFO 诊断。触摸、HA 控灯和同步尚未验收，不宣称按钮已修复 |
| App CI（主控报告） | `24bb0256` parity 修复后的完整 CI 已全绿；`68328f90` 新 CI 待跟进。与下文旧全套测试限制、内容仓库无关 404 分开记录 |
| 正式内容 | 仍为一个 preset、`enabled:false`、公开 contract 5 可验证的 review stub，等待公开 contract 13 和资源分发 |

公开依据为固件 `docs/keyless-reference-verification.md`、用户点名的 keyless JSON 和 manifest。
[本轮公开证据](evidence/e1003-keyless-reference-2026-10-15.json)原样复制无 key/密码的记录。
没有读取 AppSupport、恢复记录、其他 `.local-*` 文件或设备日志；没有操作 App/串口。
真实 factory 仅用于作者侧既有打包检查，不提交二进制。0.1 加密证据及相应旧 SHA/任务继续保留如下。

## 历史阶段：0.1.0 统一部署验收（contract 12）

[App 草稿 PR #162](https://github.com/suharvest/app_collaboration/pull/162) 已推送 `689789d9`，
标题为 `feat: deploy E1003 in-App with automatic firmware checks`。实际本地 App 页面只有
一个 deploy preset 和一个 `e1003_config` 步骤，同一表单提交后执行固件检查与配置。

| 检查 | 证据与边界 |
| --- | --- |
| 身份匹配 | Improv 核对 project/version/hardware/name；目标为 `love4yzp.e1003-dashboard` / `0.1.0` / `ESP32-S3` 及设备名称规则 |
| 完整匹配流程 | 打包后端 + 共享前端任务 `2aceff876f334cd4bd480a859b005dfd` 为 `completed`，固件 `action=skipped`；保存 65 秒、复位后加密目标读回完整通过 |
| 受控实际安装 | 仅首次 probe 故障注入为 `None`，随后通过实际 PyInstaller 同路 esptool Python API 写固定 SHA 的 factory image、`verify_flash`；真实 USB 二次读取匹配 `0.1.0`，`action=installed` |
| 配置保留 | 受控安装后原 key 与保存 target 的加密读回通过；不全片擦除，NVS 策略不变 |
| 测试条件 | 此为故障注入触发的实际写入测试，不是出厂空白设备、版本升级迁移或新 Wi-Fi 原生表单验收；不把它描述为整个安装分支从所有初态均已通过 |
| App 检查（主控报告） | 955 前端、49 Python + 5 subtests、3 项本机目录配置、7 Rust verify 检查通过；PyInstaller/Rust/Tauri 构建通过。不同于下节历史全套 Python 的结果，不宣称全套重跑绿色 |
| 提交与内容契约 | 统一实现已提交 `689789d9`、contract 12；正式内容仍为公开 contract 5 可验证的禁用 review stub，待 12 同步后接入原生执行 |
| 版本约束 | canonical manifest 和镜像未改；未来不同构建必须变更固件 `project.version`，不能同版本复用不同镜像 |

本内容会话只读取了用户逐一点名、明确不含 key/密码的 `single-flow-hardware-result.json`
和 `controlled-install-result.json`，没有枚举目录或读取其他 `.local-*` 文件，也未操作 App/串口。
[公开证据摘要](evidence/e1003-unified-flow-2026-10-15.json) 保留任务状态、固件动作与受控安装结果，
移除了设备名称、局域网地址与测试 target 值；65 秒/复位读回及 App 检查数量明确来自主控补充。
新 Wi-Fi、真实 HA 控灯、触摸与动态状态同步继续待验收。

## 历史阶段：contract 11 原生 App 配置证据

依据 App 工作基线 `50fc49df` 上新增功能的公开文档
`docs/e1003-desktop-configuration.md` 和 `docs/reports/e1003-desktop-configuration.md`，
本内容会话只读核对源码与公开报告，未访问运行中的 App、串口或 `.local-*` 私有目录。
原生实现见 [App 草稿 PR #162](https://github.com/suharvest/app_collaboration/pull/162)，最新证据对应 commit `6efdf2ee`，contract 11；未合并或发布。

| 检查 | 结果与范围 |
| --- | --- |
| 交互入口 | 桌面 App 内置 `e1003_config` 步骤，contract 11；内建 Improv / aioesphomeapi，不依赖外部网页、本机脚本路径或用户 Python |
| 实机配置 | 打包 PyInstaller 后端 + 与桌面壳共享的前端提交，任务 `71f687f325a14929bddb47cce847ddf1` 完成目标写入、65 秒保存等待、硬件复位、加密重连和持久化读回；独立加密读回也通过 |
| 配置保留 | 复用已有网络与设备 key；该次未重编译或重烧录固件 |
| 密钥处理 | 早期打包后端验证中，普通任务输出及后端日志未出现私有 key。主控最新在原生窗口显式点击复制，私下比较剪贴板与本机设备记录相等，仅输出布尔结果 `true`，并清空此次复制值；未公开密钥。本内容会话未读取剪贴板或私有记录 |
| UI 与原生启动 | 共享前端桌面/375×812 视口已检查，无横向溢出；本地隔离 Tauri debug App 成功启动、contract 11 并加载原生步骤；引擎代理及租约 smoke 通过 |
| 自动检查（App 报告） | 955 前端测试、93 项聚焦 Python 检查通过；前端生产构建、路由分组、Rust schema freshness 通过；6 项 Rust verify emulation 通过 |
| 全套 Python 限制 | 报告为 7,169 passed、288 skipped、3 failed、3 setup errors；受 macOS Bash、Linux `/proc` 与 Rust 工具链影响，工具链相关三项后续通过；不宣称全套绿色 |
| 原生窗口完整配置（主控最新补充） | 实际 macOS「SenseCraft E1003 Test」窗口通过 Accessibility 完成仅配置预设、串口选择、虚拟灯实体输入及点击保存；真实设备完成目标写入、65 秒保存、复位和加密读回，窗口显示“配置已保存”。虚拟 ID 用于配置验证，不代表真实 HA 灯控通过 |
| 介绍内容显示（主控补充） | 原生窗口已显示 technical 分类和完整中文介绍。此前已确认双语完整介绍由 Tauri App 后端返回，中文 HTML 约 1,357 字符；测试版用 `PS_FOCUS_SOLUTION_ID` 直接打开介绍。中文窗口显示与双语后端返回分别记录，不扩大为所有语言/布局均已视觉验收 |
| 尚未物理验收 | 原生表单新 Wi-Fi、真实 HA 灯控和触摸效果、动态状态/亮度同步 |

主控最新补充对应 App commit `6efdf2ee`，补齐了原生窗口操作与显式密钥复制证据；
本内容会话仅采纳上述公开结论，没有重跑设备操作或访问 `.local-*`。
本地 debug 包未公证或发布。打包后端、共享前端 QA 与原生窗口实机流程分别记录，
不合并为“完整安装版已发行/整体验收通过”。正式内容仍使用公开 contract 5 可验证的人工 stub，
当前待从 App 真源同步 contract 13 后接入统一执行类型；未擅自修改生成的 spec。

## 初始内容检查

| 检查 | 结果 |
| --- | --- |
| 源码候选 `solutionctl validate ... --spec-dir spec --check-urls` | 通过；schema、实际文件引用、双语结构和手工 verify 步骤有效 |
| 真实 factory image 大小与 SHA-256 | 1,378,512 bytes；`08d616e856cd4d48a0fef0b4e5782e3c4ac1b9efdc1e1647701707bec8bdc540` |
| 本地 staging | 成功生成独立审阅副本；未触碰串口；未启用方案 |
| staging 后 `solutionctl validate` / `steps --lang zh` | 通过；第一步真实绑定 `esp32_usb`、`devices/e1003_usb.yaml`、资源路径和真实 SHA |
| 烧录配置 schema | 对本仓库 `spec/device.schema.json` 再次校验通过 |
| 擦除选择 | 抽取本机 engine 的实际 `get_step_option()` 方法，使用生成的 YAML 运行：即使默认传入 true，`erase` 仍为 false；这是配置逻辑检查，不是设备烧录验证 |
| factory image 分区范围 | 读取构建产物内公开分区表：NVS 起点 `0x3a0000`，在此 merged image 的写入范围之外 |
| `solutionctl export` | 成功生成带固件的本地审阅 zip；root 含 `solution.yaml`；11 个文件；ZIP CRC 检查通过；包内固件 SHA 再次一致；无私密目录 |
| 新增打包测试 | 5 项通过：物化配置并保留禁用、同大小损坏拒绝、错误大小拒绝、私密路径读前拒绝、拒绝 checkout 内输出与覆盖已有审阅目录 |
| `pytest tests/test_e1003_candidate.py tests/test_solution_format.py tests/test_product_name_lint.py tests/test_untested_wording_lint.py -q` | 101 passed，14 skipped |
| 产品族离线检查 | 通过：41 个方案、118 个已知产品族；E1003 使用 `reterminal_e_series` + `purchase.require.model: [e1003]` |
| 产品名称 / 文案 lint | 0 error；产品名称 lint 有 24 条其他既有方案的 warning，本候选无新增 warning |
| Compose 命名检查 | 通过，106 个声明文件 |
| 公开仓库边界 guard | 通过；未导入或提交独立 engine 源码 |
| 新增 Markdown 本地链接 / `git diff --check` | 通过 |

格式测试文件的 `SOLUTIONS_DIR` 当前定位到本 checkout 的父目录，因此相关参数用例
被跳过；不能把这部分 pytest 结果当作新方案的渲染证明。新方案实际 EN/ZH 结构、
required config、verify 和资源文件分别由上述两次 `solutionctl validate` 校验。

复现作者侧验证：

```bash
uv run --package sensecraft-solutionctl solutionctl validate \
  solutions/reterminal_e1003_ha --spec-dir spec --check-urls
uv run --package sensecraft-solutionctl --with pytest pytest \
  tests/test_e1003_candidate.py tests/test_solution_format.py \
  tests/test_product_name_lint.py tests/test_untested_wording_lint.py -q
uv run python scripts/ci/validate_product_families.py
uv run python scripts/ci/lint_product_names.py
uv run python scripts/ci/lint_untested_wording.py
uv run python scripts/check_compose_naming.py
sh scripts/public-repo-guard.sh
git diff --check
```

## 历史阶段：App USB 实机测试

主会话在用户正在运行的 SenseCraft Solution **0.7.3**
（`http://127.0.0.1:20116`）完成了本地测试，本内容会话没有重跑导入或烧录。
测试使用独立的 `reterminal_e1003_ha_local_usb`，`enabled: true`，preset 为
`local_usb`，仅包含 `flash_panel` / `esp32_usb`。正式候选未启用。

| 检查 | 结果 |
| --- | --- |
| App 导入、资源与请求验证 | parse/apply 导入成功；资产端点返回的固件 SHA 与锁定值一致；validate 返回 `valid: true`、无警告 |
| 实际部署 | `d9140919-7b3e-4b38-83a0-f23daa1322d2`，`completed`，80.704458 秒；主会话报告 0 errors |
| 烧录参数 | 公开测试包为 `esp32s3`、115200、factory offset `0x0`；App 读回 `erase.default: false` |
| 写入校验 | 主会话日志确认 `Hash of data verified.`；公开记录的 `write_hash_verified: true` |
| 擦除范围 | `0x00000000..0x00150fff`；NVS 位于 `0x003a0000`，不在该范围内；主会话确认无全片 erase 命令 |
| 更新后配置 | 父客户端使用原设备独立 key 加密重连成功，并成功读回原 target；未在此处复制 key 或 target 值 |
| esptool 提示 | 5.1.0 输出 4 条旧拼写弃用提示：`--flash_mode`、`--flash_freq`、`--flash_size`、`write_flash`；不影响本次烧录，区别于 validate 无警告 |

证据来源为固件仓库公开的 `.esphome/local-tests/app-verification.json` 及同目录测试包。
本会话读取了这些明确授权的非私密材料，重新核对包内 ID、preset、烧录配置与固件 SHA；
未访问 `.esphome/provisioning/` 或 `.esphome/verification/`。
公开 JSON 的副本保存在 [App USB 测试记录](evidence/e1003-app-usb-2026-10-14.json)，
不提交二进制包。主会话已清理 scratch，用户 App 中的导入副本保留。

这是该轮 **App 烧录 + 父客户端配置验证** 的证据。该轮未覆盖表单传值；后续源码预览
的真实表单配置见下节。两轮均不能证明真实 HA 控灯、触摸或显示同步已经通过。

## 历史阶段：generic script 表单适配

固件 PR #2 commit `27b8b34406dd64a1d92db46fef50d590f5dd6c0c` 新增
`tools/app_configure_device.py`，复用 `configure_device` / `wait_for_network`；公开记录为
**16 tests 通过**。适配器通过现有 `script.start_command.env` 接收输入，不把密码放入
argv 或生成配置文件；复用已有私有 key 记录或首次生成，用户不需手动 CLI 或编译器。
因此「本地联调必须新增专用 deployer」的旧建议已移除。

| 检查 | 当前结果 |
| --- | --- |
| installed App 0.7.3 | 真实浏览器请求丢弃 script 输入，仅留下 host/target_type；旧后端 Script 上下文也未传值，不能直接承担此表单配置 |
| 源码预览 | App 源码 HEAD `39aee2d` 已包含前后端传值修复；主会话用隔离副本构建前端并运行源码后端，未替换安装包或修改独立 App 源码仓库 |
| 当时入口 | 旧 App 通过 `web_dashboard` 打开隔离源码预览表单；此为历史证据，当前指南已改为 App 内置原生表单 |
| 表单请求 | 真实浏览器提交通过；输入为 `usb_port`、`light_entity`、可选 Wi-Fi 名称/密码及 `copy_api_key` 布尔值 |
| 字段保留字 | 使用 `light_entity`，不使用会被解释为部署位置 selector 的 `target`；通过 env 映射到 `E1003_TARGET` |
| 实际配置任务 | `b1eaa2b8-94b4-45b9-933a-3208b1e90efd`，完成用时 **88.620004 秒** |
| 持久化完成条件 | 主会话报告原 key 复用、新测试灯绑定写入；等待 65 秒、hard reset 后加密读回通过，才报告配置成功 |
| 独立核对 | CLI verify 也通过；本轮未重编译或重烧录固件 |
| 尚待硬件验证 | 通过这份新表单配置新的 Wi-Fi；真实 HA 灯光控制和显示同步 |

公开记录为固件仓库 `.esphome/local-tests/app-configuration-verification.json`，副本见
[表单配置测试记录](evidence/e1003-app-configuration-2026-10-14.json)。
两个公开测试包为 `e1003-configurable-source-preview.zip` 和 `e1003-installed-app-entry.zip`。
本内容会话只读核对：源码包确实使用 `script`、固定平台命令、五项 env 绑定和
`E1003_CONFIGURATION_SAVED` log_pattern；旧 App 入口包的配置步骤为 `web_dashboard`。
没有运行适配器、读取私有目录、访问或改动活动预览，也没有再次导入/操作设备。

这些早期测试包依赖本机固定 venv 和适配器，属于 **local-only 历史验证**，不再是当前部署建议。
原生后端与共享前端现已打包并完成保存验证，不能继续把“尚无内建客户端/尚未打包依赖”写作当前阻塞。
旧 installed App 0.7.3 也不能据此视为具有原生步骤。

## 尚未完成的验收

1. 新 plaintext-only App 实现/验收、CI/审查与分发；公开契约由 5 同步至 14，随后替换候选 review stub。
2. 真实固件缺公开下载地址；未发布资源或修改发布清单。
3. 新原生表单配置新 Wi-Fi 的物理验证；旧客户端配网通过不能代替新表单验收。
4. HA 设备确认、动作权限、真实灯控制及触摸；任意目标状态和亮度显示同步还需 Blueprint/适配。
5. 新 0.2.1 构建和最终 size/SHA、升级/持续免密/旧记录处理、出厂空白设备、两面板隔离及支持平台；0.1.0→0.2.0 结果仅保留历史范围，OTA 关闭。

本次不重复硬件操作，不读取 key/NVS/私密备份。人工清单返回成功不能作为部署通过；
正式候选继续 `enabled: false`。

## 文案与本轮内容检查

此前已通过 Lody 完成用户指定的润色会话：
`49157746-ef4c-4fb1-b618-2f58744271cd`（去 AI 味润色）、
`6bf9a301-244b-4001-94d3-d77236908b60`（GPD）及
`0420b51f-e06e-413e-9416-befeb061f0a8`（高级工程师）。沿用已完成讨论，
本轮按 technical 定位与原生 App 新证据修订，没有重复创建会话。

### 技术演示分类与原生表单修订（2026-10-15）

`solution_type` 改为 `technical`，名称、summary 与双语首屏直接说明预编译固件、运行时配置、
测试动作及已验证边界；删除床头/办公照明等暗示实际控灯已完成的应用场景。
`output_interfaces` 仅声明现有契约支持的真实 Improv Serial 输出；加密 native API 的
TCP 6053 与绑定读回在正文说明，不伪造 HTTP、MQTT 或设备网页接口。

双语指南改为 App 内置表单、保存进度及成功后的密钥复制按钮。保留原 guide 属性块、
manual 执行类型、固定固件 SHA 和安全烧录参数；当时等待 contract 11，该轮统一部署依赖升级为 12；当前默认免密依赖为 13。
本轮复核：`solutionctl validate --check-urls` 通过；现有测试 **101 passed、14 skipped**，
其中 5 项为候选打包测试。格式用例因既有目录定位而跳过，不能视为渲染证明；候选的
schema、引用和双语属性由实际 `solutionctl validate` 检查。
产品族检查、文案 lint、公开边界 guard、Markdown 本地链接及 `git diff --check` 通过。
产品名称 lint 为 0 errors、24 条其他内容的既有 warning。本轮未导入、预览、烧录、发布或合并。

### 产品图片与架构封面

按主控提供的公开素材复制三份文件至候选 `gallery/`：官方产品原图（1800×1200）、
生成的架构封面（最终为 1774×887，适配 App 的 21:9 裁切）和来源 README。只读取用户点名的三份文件，没有访问其上层
运行目录的其他内容；未操作 App、串口或上传资源。

`intro.cover_image` 指向架构图；`intro.gallery` 和双语正文引用本地图片并标明官方展示界面、
生成示意及 HA 验收边界。`device_catalog` / `purchase.require`、禁用状态、固件清单及执行
配置不变。作者侧打包白名单加入三份素材，既有测试增加图片随审阅包原样保留的检查。

本轮 `solutionctl validate --check-urls`、产品族检查、文案 lint、公开边界 guard 通过；
现有测试为 **101 passed、14 skipped**，跳过原因同前。内容导出 zip 为 14 个文件，CRC 检查
通过，三份图库素材与源文件逐字节一致，包中无固件二进制。15 处本地链接与锚点有效；
另核对产品族选择、候选禁用状态、固件和执行字段未变。未执行本地 App 导入或 UI 验收。

主控本地预览补充：独立桌面测试 App 已导入同一套图片；原生窗口的辅助功能树显示产品图及
准确的双语说明。共享前端从 App 资源接口实际解码封面（1774×887）和实物图（1800×1200），
桌面截图确认最终封面标题、连接标注和底部说明均未被裁切。375 px 视口的图片加载正常，
页面未产生横向溢出；这不代表对移动端整体布局做了重新验收。未操作设备或重新烧录。

### 统一部署文案修订

名称、summary、唯一 preset 与双语指南统一为一份表单，用户不选择“烧录并配置 / 仅配置”。
保留三个 review 阶段的 ID/type/config 属性和 verify 清单，不将它们描述为三次提交或三个套餐。
自动检查依赖 contract 12；旧 contract 11 窗口与独立 App 烧录证据均按历史阶段保留。
图片、产品族与购买约束、canonical manifest、固件参数未改；无关 404 CI 说明保留在 PR 正文。

本轮内容校验（`--check-urls`）、产品族检查、文案 lint 和公开边界 guard 通过；现有测试
**101 passed、14 skipped**（既有目录定位限制同前）。15 处本地链接/锚点及导出 ZIP CRC 通过；
额外确认仍只有 `usb_candidate` 一个 preset、候选禁用、guide 属性块不变，固件清单和镜像参数、
图片及产品族选择未变。没有启动或调用 App，也没有执行任何设备测试。

### 统一流程最终证据补充

已用 `689789d9` 的完整匹配任务和受控实际安装结果替换上一轮“仍在测试/尚未提交”的当前结论。
保留原生窗口、独立 USB 烧录和图像展示的历史证据，并明确安装测试故障注入的范围。
本次只修改文案与公开检查记录；入口仍为一个，候选仍禁用，manifest 版本/哈希、NVS 策略与图片不变。

本次内容校验（`--check-urls`）、5 项既有打包测试、文案 lint、公开仓库边界与差异检查通过；
16 处本地链接/锚点有效。证据中的 SHA 与 canonical manifest 一致；单一 preset、禁用状态、
guide 属性块、固件版本/哈希/NVS 策略、产品族与图片未变。未重跑 App 测试或设备操作。

### 0.2.0 默认免 API 密钥修订

本轮替换当前文案中的强制加密、必需本机 key 记录和总是复制密钥的引导；旧 0.1 加密证据保持历史含义。
保留单入口和图像，Device key 图注改为可选能力；更新 manifest 与 flash-review 模板 SHA，
新增二者资源引用一致性的打包回归检查。固件版本、大小与 SHA 仅按新构建同步，安全烧录/NVS 策略不变。

本轮 `solutionctl validate --check-urls`、产品族检查、文案 lint、公开边界与差异检查通过；
现有测试 **102 passed、14 skipped**（含 6 项打包检查；既有格式目录定位的跳过限制同前）。
使用唯一获准的新 factory 路径执行既有作者打包：stage 校验 size/SHA，生成副本仍禁用，
实际 `esp32_usb` 配置再次校验通过；导出包 14 个文件、CRC 有效，包内新固件大小与 SHA 一致。
临时含 bin 的审阅包在检查结束清理，未提交二进制。15 处本地链接/锚点有效；产品族、图片、
单一入口、guide 属性块及 115200/0x0/erase=false 保持。没有为测试启动 App、读取实际 key 或操作设备。

### 0.2.1 方向纠正（构建与最终证据待补）

撤下当前页面的可选加密和 key 复制引导；0.2.0 转为历史过渡，并记录 610 秒曾通过后又要求加密的观察。
本轮没有修改 manifest/模板的旧资源值，也没有给新构建编造 SHA、size、commit 或验收状态。
图片原样保留，图注将 Device key 标为旧设计元素。候选继续禁用，等待主控最终公开材料。

本轮文案校验、6 项既有打包检查、文案 lint、产品族和公开边界检查通过；14 处本地链接/锚点有效。
仅核对现有历史资源和内容结构，不代表 0.2.1 固件/升级/持续免密通过。manifest、模板 SHA、图片、
历史证据、单一禁用入口和 guide 属性块未变；没有读取或打包未授权新镜像。

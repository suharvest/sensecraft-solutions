# E1003 运行时配置技术演示检查报告

日期：2026-10-15。结论：**分类已改为 technical；App USB 烧录和内置表单保存均有实机证据。正式候选仍禁用，公开契约同步、固件资源与 HA 验收待完成。**
接入条件见[技术演示与接入契约](e1003-ha-usb-candidate.md)。

## 本轮原生 App 配置证据

依据 App 工作基线 `50fc49df` 上新增功能的公开文档
`docs/e1003-desktop-configuration.md` 和 `docs/reports/e1003-desktop-configuration.md`，
本内容会话只读核对源码与公开报告，未访问运行中的 App、串口或 `.local-*` 私有目录。
App PR 由主控创建，链接待补充。

| 检查 | 结果与范围 |
| --- | --- |
| 交互入口 | 桌面 App 内置 `e1003_config` 步骤，contract 11；内建 Improv / aioesphomeapi，不依赖外部网页、本机脚本路径或用户 Python |
| 实机配置 | 打包 PyInstaller 后端 + 与桌面壳共享的前端提交，任务 `71f687f325a14929bddb47cce847ddf1` 完成目标写入、65 秒保存等待、硬件复位、加密重连和持久化读回；独立加密读回也通过 |
| 配置保留 | 复用已有网络与设备 key；该次未重编译或重烧录固件 |
| 密钥处理 | 普通任务输出及后端日志未出现私有 key；复制为成功后的显式操作，使用 Tauri clipboard；浏览器 QA 不能单独证明原生壳剪贴板实际操作通过 |
| UI 与原生启动 | 共享前端桌面/375×812 视口已检查，无横向溢出；本地隔离 Tauri debug App 成功启动、contract 11 并加载原生步骤；引擎代理及租约 smoke 通过 |
| 自动检查（App 报告） | 955 前端测试、93 项聚焦 Python 检查通过；前端生产构建、路由分组、Rust schema freshness 通过；6 项 Rust verify emulation 通过 |
| 全套 Python 限制 | 报告为 7,169 passed、288 skipped、3 failed、3 setup errors；受 macOS Bash、Linux `/proc` 与 Rust 工具链影响，工具链相关三项后续通过；不宣称全套绿色 |
| 尚未物理验收 | 原生表单新 Wi-Fi、真实 HA 灯控和触摸效果、动态状态/亮度同步 |

本地 debug 包未公证或发布。打包后端的硬件路径、共享前端 QA 和原生壳启动分别记录，
不合并为“完整安装版已发行/整体验收通过”。正式内容仍使用公开 contract 5 可验证的人工 stub，
待从 App 真源同步 contract 11 后接入执行类型；未擅自修改生成的 spec。

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

1. App PR 链接与兼容功能正式分发；公开契约由 5 同步至 11，随后替换候选配置 stub。
2. 真实固件缺公开下载地址；未发布资源或修改发布清单。
3. 新原生表单配置新 Wi-Fi 的物理验证；旧客户端配网通过不能代替新表单验收。
4. HA 设备确认、动作权限、真实灯控制及触摸；任意目标状态和亮度显示同步还需 Blueprint/适配。
5. 两面板隔离、支持平台安装与下载、跨版本迁移；OTA 继续关闭。

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
manual 执行类型、固定固件 SHA 和安全烧录参数，等待 App PR 与公开 contract 11 同步。
本轮复核：`solutionctl validate --check-urls` 通过；现有测试 **101 passed、14 skipped**，
其中 5 项为候选打包测试。格式用例因既有目录定位而跳过，不能视为渲染证明；候选的
schema、引用和双语属性由实际 `solutionctl validate` 检查。
产品族检查、文案 lint、公开边界 guard、Markdown 本地链接及 `git diff --check` 通过。
产品名称 lint 为 0 errors、24 条其他内容的既有 warning。本轮未导入、预览、烧录、发布或合并。

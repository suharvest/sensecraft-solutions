# E1003 HA USB 候选检查报告

日期：2026-10-14。结论：**App USB 烧录与源码预览表单配置均已实机验证；正式候选禁用，发行打包和真实 HA 验收仍待完成。**
方案与烧录配置、资源准备方法及缺失接入契约见
[候选说明](e1003-ha-usb-candidate.md)。

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

## App 本地实机测试

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

## 真实配置表单与 generic script 适配

固件 PR #2 commit `27b8b34406dd64a1d92db46fef50d590f5dd6c0c` 新增
`tools/app_configure_device.py`，复用 `configure_device` / `wait_for_network`；公开记录为
**16 tests 通过**。适配器通过现有 `script.start_command.env` 接收输入，不把密码放入
argv 或生成配置文件；复用已有私有 key 记录或首次生成，用户不需手动 CLI 或编译器。
因此「本地联调必须新增专用 deployer」的旧建议已移除。

| 检查 | 当前结果 |
| --- | --- |
| installed App 0.7.3 | 真实浏览器请求丢弃 script 输入，仅留下 host/target_type；旧后端 Script 上下文也未传值，不能直接承担此表单配置 |
| 源码预览 | App 源码 HEAD `39aee2d` 已包含前后端传值修复；主会话用隔离副本构建前端并运行源码后端，未替换安装包或修改独立 App 源码仓库 |
| 用户入口 | `127.0.0.1:20116` 的本地配置步骤通过 `web_dashboard` 打开 `127.0.0.1:54359` 的可编辑表单；浏览器弹窗已验证 |
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

测试包依赖本机固定 venv 和适配器路径，属于 **local-only**；不提交这些路径或二进制。
正式候选仍是禁用的说明与资源准备内容。发行尚需 runtime/dependency bundle、受支持的
适配器入口和 installed App 更新，不能把当前跨页面预览描述为已交付的完整安装版能力。

## 尚未完成的验收

1. 没有公开固件 URL，未执行资源发布。
2. generic script 本地适配与源码表单传值已通过；正式候选不带本机路径，发行所需
   runtime/dependency bundle、适配器入口和 installed App 更新仍未完成。
3. 本地独立副本已完成烧录和可编辑表单配置；安装、配置的一次连续提交及正式候选
   的完整界面仍需后续验收。
4. HA 设备确认、动作权限、真实灯控制/触摸、任意目标状态与亮度同步、两面板隔离、
   支持平台安装及资源下载均须按接入契约完成验收。
5. 新 Wi-Fi 经新表单的硬件测试尚待完成；OTA 关闭，不得启用无鉴权 OTA，跨版本迁移也未验收。

固件侧既有 11 tests 与单机 USB 配置/保留证据见固件项目公开验证记录。
真实 HA 控灯仍等待用户提供 HA 地址和 `light.xxx` 实体。
本内容会话没有重跑硬件操作，也没有读取 key/NVS/私密备份。
`enabled: false` 是候选交付的必要状态。禁止把人工清单自动完成解释为部署成功。

## 文案修订

面向用户的介绍页、部署页及步骤名称已删去工程审查、测试记录、分区参数和维护者
打包说明；这些信息保留在开发文档与资源说明中。用户页面保留用途、适用条件、
配置流程及当时的 App 配置/动态同步限制；后续表单能力按上文新证据更新。

通过 Lody 创建了「去 AI 味润色」角色会话
`b6602a73-9e94-4366-8354-5a9b6724c4f5`，角色 ID 为
`49157746-ef4c-4fb1-b618-2f58744271cd`，完成 EN/ZH 文案润色，再由父会话复核事实边界。

修订后 `solutionctl validate --check-urls`、5 项打包测试、产品族检查、文案 lint、
边界 guard、链接和差异空白检查通过。对比修订前后，guide 属性块及 YAML 执行字段
一致，`enabled: false` 保留。文案修订时重新导出的内容预览 zip 不含固件；
后续 App 实机测试使用上文主会话的独立测试副本。
未上传二进制或操作 CDN，也未执行 merge 或发布。

### 按钮绑定与部署说明调整

与用户指定的 GPD 文案角色及高级工程师完成两轮讨论后，用户页面统一使用
「按钮控制的灯」，明确开关及四档亮度共用一个灯光绑定，保留面板的时钟与温湿度定位。
部署说明按安装、联网并设置按钮、HA 启用控制组织；参数采用单列，连接密钥留到
HA 接入阶段，安装成功、设置保留和实际控灯分别确认。
未来「先配置、再安装」只收集会话内输入，设备启动后再写入；该轮内容改版未新增 App 表单，
后续由主会话的 script 本地适配器和源码预览提供可执行配置。
具体布局和状态短句见[部署页注意力与参数布局](e1003-ha-usb-candidate.md#部署页注意力与参数布局)。

本次方案校验、5 项打包测试、产品族检查、文案 lint、公开边界及本地链接检查通过。
执行字段、guide 属性块及 `enabled: false` 均与修改前一致；未重跑任何设备测试。

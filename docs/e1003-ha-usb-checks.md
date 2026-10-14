# E1003 HA USB 候选检查报告

日期：2026-10-14。结论：**可审阅的禁用内容候选；App 全流程仍阻塞。**
方案与烧录配置、资源准备方法及缺失接入契约见
[候选说明](e1003-ha-usb-candidate.md)。

## 本轮结果

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

## 尚未通过的 gate

1. 没有公开固件 URL，未执行资源发布。
2. App/engine 缺少已接入的 Improv、runtime key 和原生 API 目标写入路径；源码候选
   无用户输入表单；本地物化包只给出可审阅的烧录执行配置。
3. 未进行 App 导入与视觉预览，也未从 App 烧录；需要实际 API Access 端口及后续实机协调。
4. HA 设备确认、动作权限、真实灯控制/触摸、任意目标状态与亮度同步、两面板隔离、
   支持平台安装及资源下载均须按接入契约完成验收。
5. OTA 关闭；不得启用无鉴权 OTA。跨版本配置迁移没有此轮证据。

固件侧既有 11 tests 与单机 USB 配置/保留证据见固件项目公开验证记录；本轮没有
重跑那些硬件操作，没有把它们算作 App 验证，也没有读取 key/NVS/私密备份。
`enabled: false` 是候选交付的必要状态。禁止把人工清单自动完成解释为部署成功。

## 文案修订

面向用户的介绍页、部署页及步骤名称已删去工程审查、测试记录、分区参数和维护者
打包说明；这些信息保留在开发文档与资源说明中。用户页面保留用途、适用条件、
配置流程及 App 配置/动态同步尚未完成的限制。

通过 Lody 创建了「去 AI 味润色」角色会话
`b6602a73-9e94-4366-8354-5a9b6724c4f5`，角色 ID 为
`49157746-ef4c-4fb1-b618-2f58744271cd`，完成 EN/ZH 文案润色，再由父会话复核事实边界。

修订后 `solutionctl validate --check-urls`、5 项打包测试、产品族检查、文案 lint、
边界 guard、链接和差异空白检查通过。对比修订前后，guide 属性块及 YAML 执行字段
一致，`enabled: false` 保留。已重新导出不含固件的内容预览 zip，未导入 App。
本次未上传二进制或操作 CDN，也未执行 merge 或发布。

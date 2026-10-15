# E1003 灯光面板配置演示：接入说明

正式候选为 technical、`enabled:false`、一个 `usb_candidate` preset。
公开 contract 5 下仅保留一个 `review_setup` manual 步骤，标记 `verify=true`；人工确认不执行设备 I/O。
待公开契约同步后，用单个原生 `e1003_config` 替换，不增加“烧录 / 仅配置”套餐。
正文无图片，仅保留一张卡片封面；设备产品图由产品目录按 `purchase.require.model=[e1003]` 提供，不在方案中硬编码图片或 SKU 链接。

## 单一配置流程

1. 连接 USB，选择串口；从 HA 实体设置复制按钮控制的灯 `light.*`。
2. 已保存的 Wi-Fi 可留空复用；首次或换网填写 2.4 GHz 名称和密码，不声称已探测到设备网络。
3. 点击“保存配置”。App 核对 project/version/hardware/name；匹配则跳过安装，否则先校验镜像大小/SHA，再安装并复核身份。
4. 写入绑定后至少保持通电 65 秒；复位并读回后显示“配置已保存并验证”。倒计时归零不代表成功。
5. 仅成功后显示设备地址和 HA 下一步：添加 ESPHome 设备、允许执行动作，再验证实际控灯。

参考固件 0.2.1 固定明文 native API，无 API 密钥控件、MQTT 或设备 web server，仅支持 USB 更新。
开发者固件独立保留加密，不属于本参考构建。

## 固件资源约束

[manifest](../solutions/reterminal_e1003_ha/assets/firmware/manifest.json) 是资源真源：

| 项目 | 固定值 |
| --- | --- |
| 固件 | `love4yzp.e1003-dashboard` / `0.2.1` / ESP32-S3；源码 `09b3bbb` |
| Factory | 1,337,072 B；`assets/firmware/firmware.factory.bin` |
| SHA-256 | `23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528` |
| 写入 | 115200、offset `0x0`、4 MB 布局、不全片擦除；保留 NVS（起始 `0x3a0000`） |
| 下载 | 公网 URL 尚缺；不提交 bin 或猜测下载地址 |

不同构建必须使用不同的固件 `project.version`，同步 source/version/size/SHA 与模板。
[作者打包工具](../scripts/stage_e1003_candidate.py)保留大小、SHA、路径与禁用状态检查；
生成的本地副本仅用于审阅 USB 固件载荷，不代表 App 完整配置或硬件验收。
用法见[资源说明](../solutions/reterminal_e1003_ha/assets/firmware/README.md)。

## 当前验证与发行依赖

- App [PR #162](https://github.com/suharvest/app_collaboration/pull/162) 最终精简提交 `a597ccad`，contract 15：`solution_id` 必填；移除 `encrypt_api`、key-copy 端点、加密迁移及磁盘 key/state 记录。协议只在 App 实现；固件仓库 `9e6ab75` 已删除重复 CLI/adapter 和历史报告。
- 当前软件检查：60 backend + 5 subtests、964 frontend、contract freeze/route checks、Black/Ruff、PyInstaller 和 contract 15 Rust sidecar 构建通过。已有 Ego 模拟与桌面/375×812 视口检查通过；Playwright 本地未运行。
- 原生 macOS 窗口已核对默认折叠、无密钥控件和成功前显隐；未点击保存、未创建真实 setup job。
- **0.2.1 最终硬件上传未验收**；触摸、真实 HA 控灯、新 Wi-Fi、升级迁移、持续免密与动态状态/亮度同步均未验收。五个灯光区域定义动作不等于实测通过；同步仍需 HA Blueprint 或适配。
- App contract 15 已提交；内容仓库公开契约仍为 5，需同步后才能替换原生步骤。兼容 App 分发、固件公网 URL 与实机验收仍是发行依赖。
- App 完整 CI 尚有 Rust 方案快照差异；内容 CI 曾因无关方案的 `supervisor_0.5.6_riscv64.deb` 返回 404，见[原日志](https://github.com/suharvest/sensecraft-solutions/actions/runs/38673057418/job/116220379050)。不宣称完整 CI 全绿。

## 离线检查

```bash
uv run --package sensecraft-solutionctl solutionctl validate solutions/reterminal_e1003_ha --spec-dir spec --check-urls
uv run python -m unittest discover -s tests -p test_e1003_candidate.py
uv run python scripts/ci/validate_product_families.py
sh scripts/public-repo-guard.sh
```

[双语操作指南](../solutions/reterminal_e1003_ha/guide_zh.md) · [固件 PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2)

# 方案设计与执行计划：SenseCraft 方案参数知识传递与 Agent 扩展机制

## 1. 目标与背景

打通从**设备方案（Solution）元数据**到 **AI Agent（如 Solution Bot、HA 对话助手、MCP Agent）** 的双向知识与参数传递机制。
以 `reterminal_e1003_ha`（墨水屏中控面板）为标杆方案，实现：
1. **知识透传**：方案定义的可改动参数（槽位、WiFi、模式等）及其技术/业务说明，能够以结构化格式无损导出给 Agent。
2. **CLI 传参驱动**：扩展 `solutionctl deploy`，支持无头 Agent 通过 `--input KEY=VALUE` 或 `--inputs-file` 动态注入参数；新增 `solutionctl schema` 供 Agent 自省。
3. **App 运行时能力与契约对齐**：对齐 `CONTRACT.md`（Contract 15），保持 `user_inputs` 与 `output_interfaces.capabilities` 的标准化。
4. **标杆方案落实验收**：使 `reterminal_e1003_ha` 具备“离线演示默认值 + 部署参数注入 + HA 自动发现与场景控制”的开箱即用能力，并通过自动化测试校验。

---

## 2. 现状诊断与证据

通过查阅 `sensecraft-solutions`、`packages/solutionctl` 及 `app_collaboration` 源码：
1. **参数定义现状**：
   - `provisioning_station/models/device.py#L777-L810` 定义了 `UserInputConfig`（含 `id`, `name`, `type`, `default`, `description`, `reconfigurable` 等字段）。
   - 各方案在 `devices/*.yaml` 中以 `user_inputs:` 声明，并在部署时由 `base.py#_build_substitution_context` 替换 `{{VAR}}`。
2. **CLI 短板**：
   - `packages/solutionctl/src/solutionctl/commands/deploy.py` 目前仅支持 `--connection`, `--preset`, `--device`，**缺乏 `--input` / `--inputs-file` 传参接口**，导致 Agent 在 CLI 环境下无法动态注入自定义参数。
   - 缺乏专门供 Agent 进行自省（Introspection）的 Schema 导出命令（如 `solutionctl schema <id> --json`）。
3. **方案元数据短板**：
   - `solution.yaml` 中的 `output_interfaces` 多为非结构化文本，缺少类似事件与槽位的结构化 `capabilities` 声明。

---

## 3. 详细架构改造方案

### 模块 A：`solutionctl` 命令行能力扩展
1. **参数注入支持** (`deploy.py`):
   - 增加 `--input`（多值键值对，如 `--input ha_light_entity=light.living_room`）和 `--inputs-file`（JSON/YAML 文件）。
   - 将这批输入合并至 engine 调用参数或环境变量中，提供给底层部署器。
2. **Schema 导出命令** (`schema.py` / `solution.py`):
   - 新增 `solutionctl schema <solution_id> [--preset <preset_id>] --json`。
   - 输出符合 OpenAI/Anthropic/MCP Function Calling 格式的 JSON Schema，包含每个 `user_input` 的 id、类型、默认值与 description 知识描述。

### 模块 B：标杆方案 `reterminal_e1003_ha` 规范落地
1. **设备部署参数化** (`devices/e1003_usb.yaml`):
   - 声明 `user_inputs`：
     - `ha_light_entity`: 目标控制灯实体（默认 `light.deskside_lamp`，`reconfigurable: true`）；
     - `WIFI_SSID` / `WIFI_PASSWORD`: 局域网 WiFi 凭据；
     - `ha_co2_entity` / `ha_energy_total_entity`: 环境与能耗槽位实体映射；
     - `scene_1_name` .. `scene_6_name`: 6 大场景名称映射。
2. **方案输出契约** (`solution.yaml`):
   - 完善 `output_interfaces`，声明 `esphome_native_api` 与 `capabilities`（包含 6 个触控场景事件 `esphome.e1003_scene_action` 及动态显示槽位）。
3. **固件与资产对齐**:
   - 产物采用 `assets/original_v5.png`（干净挖孔、Scene Control 标题）及生成的位图头文件；
   - 保持免密 Native API，开箱即用回退默认值。

### 模块 C：测试与规范验证
1. 在 `packages/solutionctl/tests/` 增加 `--input` 命令行解析与 `schema` 导出的单元测试；
2. 运行 `solutionctl validate solutions/reterminal_e1003_ha` 保证契约符合当前 Spec。

---

## 4. 实施里程碑与验收标准

| 阶段 | 任务目标 | 交付产物 | 验收标准 |
|---|---|---|---|
| **Phase 1: 审查与评审** | 将本设计提交 Codex 独立审查 | 审查报告与优化意见 | Codex 审核通过无阻碍性架构缺陷 |
| **Phase 2: CLI 扩展实现** | 扩展 `solutionctl` 传参与 Schema 导出 | `packages/solutionctl/src/solutionctl/commands/deploy.py` 等 | 单元测试通过，CLI 支持 `--input` 和 `schema --json` |
| **Phase 3: 方案元数据落地** | 完善 `reterminal_e1003_ha` 方案配置 | `solution.yaml`, `devices/e1003_usb.yaml` | `solutionctl validate` 通过 |
| **Phase 4: 双重验收** | Codex 代码 review + 本地端到端校验 | 最终测试执行与验证记录 | 契约校验 100% 绿灯，回归无破坏 |

---

## 5. Codex 审查关注点（Review Prompts）
- 契约兼容性：扩展是否会破坏当前 closed-source engine 或 contract 15 的向下兼容？
- 最小改动原则：CLI 与方案层面的参数传递设计是否过度设计？
- 边界安全：`user_inputs` 是否妥善处理密码/敏感输入（`secret` 类型脱敏）？

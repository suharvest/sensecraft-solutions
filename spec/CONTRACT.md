<!-- contract_version: 1 -->
# SenseCraft Solution Contract

> **GENERATED FILE — mechanical sections only.** Regenerate with
> `uv run python scripts/export_spec.py`. The drift guard is
> `tests/unit/test_contract_freeze.py`.
>
> `contract_version: 1`. Tables below are rendered from the
> committed `spec/*.json` artifacts. The "Derived rules" prose sections are
> **human-authored** and preserved across regenerations (they live between
> `<!-- AUTHORED:<key> BEGIN/END -->` sentinels) — the generator never
> overwrites their contents.

This document describes the machine-readable contract between the closed-source
provisioning engine and open-source consumers. Authoritative artifacts:

| Artifact | Source |
|----------|--------|
| `spec/solution.schema.json` | `Solution.model_json_schema()` |
| `spec/device.schema.json` | `DeviceConfig.model_json_schema()` |
| `spec/capabilities.json` | `DEPLOYER_REGISTRY` + `contract.REQUIRED_CONFIG` |
| `spec/plugin.schema.json` | hand-written (plugin_manager validation) |
| `spec/openapi.json` | `app.openapi()` (route introspection) |
| `spec/plugin-ctx.d.ts` | `frontend/src/modules/plugin-loader.js` ctx |


## Solution schema fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | string | no | 1.0 |  |
| `id` | string | yes |  |  |
| `name` | string | yes |  |  |
| `name_i18n` | object | no | {} |  |
| `enabled` | boolean | no | True |  |
| `intro` | SolutionIntro | yes |  |  |
| `deployment` | SolutionDeployment | yes |  |  |
| `base_path` | string \| null | no | None |  |
| `has_description` | boolean | no | False |  |
| `has_description_i18n` | object | no | {} |  |
| `has_guide` | boolean | no | False |  |
| `has_guide_i18n` | object | no | {} |  |
| `flags_base_path` | string \| null | no | None |  |

## Device schema fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | string | no | 1.0 |  |
| `id` | string | yes |  |  |
| `name` | string | yes |  |  |
| `name_i18n` | object | no | {} |  |
| `type` | string | yes |  |  |
| `inherit_host_from` | string \| null | no | None |  |
| `detection` | DetectionConfig \| null | no | None |  |
| `firmware` | FirmwareConfig \| null | no | None |  |
| `docker` | DockerConfig \| null | no | None |  |
| `docker_remote` | DockerRemoteConfig \| null | no | None |  |
| `ssh` | SSHConfig \| null | no | None |  |
| `package` | PackageConfig \| null | no | None |  |
| `script` | ScriptDeploymentConfig \| null | no | None |  |
| `nodered` | NodeRedConfig \| null | no | None |  |
| `binary` | BinaryConfig \| null | no | None |  |
| `ha_integration` | HAIntegrationConfig \| null | no | None |  |
| `video` | PreviewVideoConfig \| null | no | None |  |
| `mqtt` | PreviewMqttConfig \| null | no | None |  |
| `overlay` | PreviewOverlayConfig \| null | no | None |  |
| `display` | PreviewDisplayConfig \| null | no | None |  |
| `behavior` | PreviewBehaviorConfig \| null | no | None |  |
| `serial_camera` | SerialCameraConfig \| null | no | None |  |
| `voice_demo` | VoiceDemoConfig \| null | no | None |  |
| `voice_chat` | VoiceDemoConfig \| null | no | None |  |
| `http_debug` | HttpDebugConfig \| null | no | None |  |
| `image_predict` | ImagePredictConfig \| null | no | None |  |
| `text_chat` | TextChatConfig \| null | no | None |  |
| `image_text_chat` | ImageTextChatConfig \| null | no | None |  |
| `image_text_to_image` | ImageTextToImageConfig \| null | no | None |  |
| `serial_wizard` | SerialWizardConfig \| null | no | None |  |
| `web_dashboard` | WebDashboardConfig \| null | no | None |  |
| `robot_inspect` | RobotInspectConfig \| null | no | None |  |
| `actions` | ActionsConfig \| null | no | None |  |
| `files` | array<FileUploadConfig> | no | [] |  |
| `influxdb` | object \| null | no | None |  |
| `user_inputs` | array<UserInputConfig> | no | [] |  |
| `device_detection` | array<DeviceDetectionProbe> | no | [] |  |
| `pre_checks` | array<PreCheck> | no | [] |  |
| `steps` | array<DeploymentStep> | no | [] |  |
| `post_deployment` | PostDeploymentConfig | no |  |  |
| `network_region` | string | no | auto |  |
| `base_path` | string \| null | no | None |  |

## Deployer capabilities

| Deployer type | Required config fields |
|---------------|------------------------|
| `docker_deploy` | _(none)_ |
| `docker_local` | `docker`, `docker.compose_file` |
| `docker_remote` | `docker_remote`, `docker_remote.compose_file` |
| `esp32_usb` | `firmware`, `firmware.flash_config` |
| `ha_integration` | `ha_integration`, `ha_integration.domain`, `ha_integration.components_dir` |
| `himax_usb` | `firmware`, `firmware.flash_config`, `firmware.source` |
| `http_debug` | _(none)_ |
| `image_predict` | _(none)_ |
| `image_text_chat` | _(none)_ |
| `image_text_to_image` | _(none)_ |
| `manual` | `steps[]` |
| `preview` | _(none)_ |
| `recamera_cpp` | `binary` |
| `recamera_nodered` | `nodered`, `nodered.flow_file` |
| `robot_inspect` | _(none)_ |
| `script` | `script` |
| `serial_camera` | _(none)_ |
| `serial_wizard` | `serial_wizard` |
| `ssh_deb` | `ssh`, `package` |
| `text_chat` | _(none)_ |
| `verify` | _(none)_ |
| `video_stream` | _(none)_ |
| `voice_chat` | _(none)_ |
| `voice_demo` | _(none)_ |
| `web_dashboard` | _(none)_ |

## guide.md heading keywords

Canonical heading keywords are defined in [`docs/guide-heading-keywords.md`](../docs/guide-heading-keywords.md), the single source of truth. Summary:

| Level | Type | EN keyword | ZH keyword |
|-------|------|-----------|-----------|
| `##` | Preset | `Preset:` | `套餐:` / `套餐：` |
| `##` | Step | `Step N:` | `步骤 N:` / `步骤N：` |
| `###` | Target | `Target:` | `部署目标:` / `部署目标：` |
| `###` | Mode | `Mode:` | `模式:` / `模式：` |
| `###` | Troubleshooting | `Troubleshooting` | `故障排查` / `故障排除` |
| `###` | Wiring | `Wiring` | `接线` |
| `###` | Prerequisites | `Prerequisites` | `前置条件` |
| `###` | Deployment Complete | `Deployment Complete` | `部署完成` |


## Derived rules (human-authored)

> The prose under each heading below is **human-authored** and preserved across `export_spec.py` runs (it lives between `<!-- AUTHORED:<key> BEGIN/END -->` sentinels). The generator never rewrites authored text — it only regenerates the headings and sentinels. Edit prose *inside* the sentinels; do not move or remove them.

### docker_deploy view 派生规则

<!-- AUTHORED:docker_deploy_view BEGIN -->
A device YAML written as `type: docker_deploy` is a single authoring-time
shape. At load time `derive_docker_views()` splits it into two legacy-format
views — a `docker_local` view and a `docker_remote` view — that the rest of the
engine consumes unchanged. The split follows these rules (source:
`provisioning_station/services/solution_manager.py:316-445`).

1. **`remote_path` is required (no `solution_id` fallback).** The remote view's
   path must come from either `docker.remote_path` or
   `remote_overrides.remote_path` (override wins). There is **no** automatic
   fallback to `solution_id` — a project's deploy directory rarely equals its
   solution id, and the old fallback silently produced wrong paths. The resolved
   value is validated as a non-empty, non-whitespace string: `""`, whitespace,
   `null`, or a missing key all raise `ValueError` (`:405`). Use a value like
   `/home/{{username}}/<project-dir>`.

2. **`compose_dir` normalization for `..` paths.** If `docker.compose_file`
   contains `..` (e.g. `../docker/x.yml`) and no `compose_dir` is supplied
   anywhere (neither in `docker` nor `remote_overrides`), the derived
   `docker_remote.compose_dir` becomes the **basename of the parent directory**
   (`docker`), not the literal `../docker`, which is meaningless inside the
   remote workspace (`:348-353`, `:440-445`).

3. **`remote_overrides.actions` is a FULL REPLACE, not merge/append.** The
   entire `actions` block under `remote_overrides` replaces the base `actions`
   block wholesale for the remote view. To "keep the base actions **and** add a
   remote-only one" you must copy every base action into
   `remote_overrides.actions` and then add the new one — otherwise the base
   actions silently disappear from the remote view. When the override's
   `actions.before` shares **zero** action names with `base.actions.before`, a
   `logger.warning` is emitted (a strong hint the author thought they were
   appending); the warning is suppressed once any name overlaps (`:355-368`).

4. **`device_class` profile is prepended and name-deduped.** When the base YAML
   carries a `device_class:` key, the matching device-class profile is
   auto-loaded; its `actions.before` / `actions.after` and `pre_checks` are
   **prepended** to whatever the base YAML defines, with **name-based
   deduplication** — a profile action whose `name` already exists in the base is
   skipped (idempotent) (`:330-336`).

5. **View field partitioning.** The **local view** drops `remote_overrides` and
   `ssh`, and is tagged `type: docker_local` (`:423-429`). The **remote view**
   drops `remote_overrides` and `docker` (its docker config is re-attached as a
   `docker_remote` block), and is tagged `type: docker_remote` (`:431-437`).
   `device_class` is a meta hint and is stripped from **both** views (`:416-421`).
<!-- AUTHORED:docker_deploy_view END -->

### 资源路径解析

<!-- AUTHORED:resource_path_resolution BEGIN -->
All resource paths declared in a solution's YAML/Markdown are **relative to the
solution's `base_path`** (its on-disk directory). There is no extra prefix and
no per-resource root — paths are joined directly onto `base_path`.

- **Solution assets** (`Solution.get_asset_path`,
  `provisioning_station/models/solution.py:426-432`): returns
  `Path(self.base_path) / relative_path`. Used for solution-level assets
  (gallery images, etc.). Returns `None` when `base_path` or the relative path
  is empty; it does not check existence.

- **Device assets** (`DeviceConfig.get_asset_path`,
  `provisioning_station/models/device.py:932-948`): same join,
  `Path(self.base_path) / relative_path`, but with one extra rule — if the
  relative path is **already absolute** it is returned as-is. This handles paths
  that `resource_resolver` has already resolved from a cloud URL to a local
  cache path. Returns `None` for an empty path, or when `base_path` is unset and
  the path is relative.

- **Markdown content** (`SolutionManager.load_markdown`,
  `provisioning_station/services/solution_manager.py:1127-1148`): resolves
  `Path(solution.base_path) / relative_path` (e.g. `description.md`,
  `guide_zh.md`). Missing `base_path` or a non-existent file logs a warning and
  returns `None`; the file is read UTF-8 and optionally rendered to HTML.

- **Device YAML config** (`SolutionManager.load_device_config`,
  `provisioning_station/services/solution_manager.py:1343-1349`): resolves the
  device config file as `Path(solution.base_path) / config_file` (the
  `config=devices/x.yaml` value from guide.md). The device id is derived from
  the file stem (`Path(config_file).stem`). Missing file logs a warning and
  returns `None`.
<!-- AUTHORED:resource_path_resolution END -->

### guide.md Step/Target 语法

<!-- AUTHORED:guide_step_target_syntax BEGIN -->
Steps and their sub-sections are declared as Markdown headings with a
`{#id ...}` attribute block. Source:
`packages/sensecraft-solution-spec/src/sensecraft_solution_spec/markdown_parser.py`.

**Step header** — `## Step N: Title {#step_id type=xxx config=devices/x.yaml ...}`.
The attribute block after `{#id` is parsed by `parse_step_attributes()`
(`:316-334`) as space-separated `key=value` pairs; values may be quoted
(`"..."`) or unquoted, and the literals `true`/`false` become booleans. The
attributes are mapped onto the `DeploymentStep` at `:795-804`:

- **`type=`** — the deployer/step type (required). Validated against the set of
  valid step types; an unknown or missing type is a parse error (`:714-736`).
- **`config=`** — relative path to the device YAML for this step (e.g.
  `devices/docker.yaml`), stored as `config_file`. Resolved relative to the
  solution `base_path` (see "资源路径解析" above).
- **`required=`** — whether the step is mandatory; defaults to `true` when
  omitted (`:799`).
- **`verify=`** — when `true`, marks the step as a verify-capable step
  (`verify_override`), e.g. `{#demo type=manual verify=true}` so a manual demo
  step is treated as a verification step (`:802`).
- **`target_inherit_from=`** — id of another step whose Target/Mode list this
  step reuses instead of redeclaring it (`:803`).

**Target / Mode sub-sections** — declared as `###` headings *inside* a Step's
body and associated with the enclosing Step:

- **Target**: `### Target: Name {#id config=xxx default=true}` (EN) /
  `### 部署目标: 名称 {#id ...}` (ZH). The name is optional; when omitted the
  frontend resolves the display name from i18n via `type=local`/`type=remote` +
  `device_name=` (`TARGET_HEADER_PATTERN`, `:279-288`). Targets are only parsed
  for `docker_deploy` and `recamera_cpp` step types (`:806-808`), via
  `parse_targets()` (`:949-982`), which merges EN/ZH by target id. Each target's
  attributes (`config`, `default`, `device`, `device_name`, `type`) come from
  the same `parse_step_attributes()` (`:909`, `:935-943`).
- **Mode**: `### Mode: Name {#id ...}` (EN) / `### 模式: 名称 {#id ...}` (ZH)
  (`MODE_HEADER_PATTERN`, `:289-293`; parsed at `:985-1012`). Mode parsing stops
  when a Target header is reached (`:996-997`), so Modes belong to the Step body
  preceding any Targets.

Other recognized `###` sub-sections within a Step — `Prerequisites` (`前置条件`),
`Wiring` (`接线`), `Troubleshooting` (`故障排查`/`故障排除`), `Deployment Complete`
(`部署完成`) — are matched by `SUBSECTION_PATTERNS` (`:299-312`) and folded into
the Step's section content.
<!-- AUTHORED:guide_step_target_syntax END -->

### extra 字段处理

<!-- AUTHORED:extra_field_handling BEGIN -->
**Warning: unknown fields are silently dropped, not rejected.** The solution
and device models inherit Pydantic's default `extra="ignore"` behavior. Any
field a consumer writes that is not declared in the schema is **silently
discarded** on load — it does not raise and does not round-trip. Do not rely on
extra keys surviving a load/dump cycle.

A grep of `model_config` / `ConfigDict` / `extra=` across
`provisioning_station/models/` shows **no model sets `extra="forbid"`**. The
only explicit `model_config` settings are:

- `ActionConfig` (`provisioning_station/models/device.py:437-440`):
  `ConfigDict(populate_by_name=True)` — this controls field-alias population,
  **not** extra-field rejection. (Despite earlier notes, it is *not* an
  `extra="forbid"` exception.)
- `provisioning_station/models/tailscale_state.py:23,40,50` and the request/
  response models in `provisioning_station/models/websocket.py`:
  `ConfigDict(extra="allow")` — these intentionally **keep** unknown fields
  (runtime state / WS payloads), the opposite of forbidding them.

In short: there is currently **no schema in `models/` that forbids extra
fields**. Treat unknown keys as best-effort and verify a model's `model_config`
before assuming round-trip fidelity.
<!-- AUTHORED:extra_field_handling END -->

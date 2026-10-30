# Deploy a solution

Run Step 0 in `SKILL.md` first. Use `--lang zh` for a Chinese user and `--lang en` for an English user. The examples below use the absolute Engine path injected into the installed Skill; keep that path in place of `sensecraft-engine` when required.

## 1. Find the solution

```bash
solution-cli hub search "<user request>" --limit 5 --json
solution-cli hub get <reference-design-id> --locale <en|zh|ja> --section deployment --json
sensecraft-engine solution list --json
```

The Hub record identifies the business Scenario, its related Tech/RD records,
the deployment-document mapping, and production links. Match the request to a
Reference Design first; do not treat a Scenario or Tech page as an executable
solution. Then use the Engine's local list and `deploy-info` to confirm that
the mapped `solution_id` and presets are actually installed. If several RDs
fit, explain the difference and ask which one to use.

## 2. Read what the deployment needs & schema

```bash
# 1. Inspect standard Draft-07 JSON Schema and external output data interfaces:
sensecraft-engine schema <id> --json

# 2. Or inspect deployment steps, hardware presets, and required parameters:
sensecraft-engine deploy-info <id> --lang zh
sensecraft-engine doctor --json
sensecraft-engine device ports
sensecraft-engine device scan --timeout 5
```

The `schema` command returns:
- `inputs`: Standard Draft-07 JSON Schema defining all accepted and required parameters per step, including target and mode conditional requirements (`allOf` with `if`/`then`) and parameter type definitions.
- `output_interfaces`: Data ingestion specifications (MQTT topics, REST endpoints, TCP streams, and payload schemas) provided by the solution.

> [!NOTE]
> **Engine Capability & Versioning**: `sensecraft-engine schema`, direct inputs (`--input` / `-i`), and `--inputs-file` are supported on `sensecraft-engine >= 0.0.6`. If running an earlier version (e.g. 0.0.3), upgrade via `curl -fsSL https://sensecraft-statics.seeed.cc/solution-app/engine/install.sh | sh -s -- --with-content` or fall back to `sensecraft-engine deploy-info <id>` with Method B (`--params ./.sensecraft-work/body.json`).

Read `presets[]`, `steps[]`, `device_connections`, `selected_devices`, and `request_template` from `deploy-info` or `schema`. A preset with more than one variant requires the user's choice. Fill every `<REQUIRED: ...>` value from the user or a read-only device check; never invent device IDs, connection keys, SSH credentials, serial ports, Docker targets, or mode IDs.

### Step Selection: Core Hardware, Container Services, and Integrations

When a solution preset contains core hardware flashing steps (such as `esp32_usb`, `himax_xmodem`), optional container services (such as `docker_deploy`), and integration steps (such as `ha_integration` connecting via HTTP/API):
1. **Prefer Remote Target / Auto-Discovery for Container Services**:
   - For services supporting `remote` targets (e.g. `ha_remote`), the device definition supports `network_scan` detection.
   - Run `sensecraft-engine device scan --timeout 5` to discover reachable SSH devices on the LAN (e.g. Raspberry Pi, reComputer, home server).
   - If reachable hosts exist, prompt the user with detected candidates or ask for their target host IP, rather than assuming local execution.
2. **Selective `selected_devices` (Avoid `ERR_PRECHECK`)**:
   - If targeting local Docker, **Verify Local Docker Availability First**: Run `sensecraft-engine doctor --json`.
   - If local Docker is not installed, not running, or running in an environment without native host networking support (such as Docker Desktop on macOS or Windows where host network mode cannot support Home Assistant mDNS and LAN device discovery), **`selected_devices` MUST only exclude local container service steps whose prerequisites are unfulfilled** (e.g. excluding a `docker_deploy` step like `deploy_ha` when targeting local Docker).
   - Integration steps connecting to an existing external or independent service (such as `connect_ha` via HTTP/API) do not depend on local Docker and SHOULD be retained in `selected_devices` alongside the hardware steps whenever an existing instance is available.
   - Do NOT blindly select all steps in `selected_devices`. When required connection parameters for `remote` (such as `host` and SSH credentials) have not been provided by the user, the step MUST remain pending or excluded, preventing premature execution.
   - When the user selects remote container deployment, dynamically match an available remote target from `step.targets` where `type == "remote"`, populate SSH connection fields, and let remote preconditions inspect whether the service is already running on the target host before attempting Docker deployment.

### Understanding Targets vs Modes (`has_targets` vs `has_modes`)

Each step in `steps[]` can deploy to different infrastructure locations (`has_targets: true`), support different hardware models or application configurations (`has_modes: true`), or have fixed parameters (both false). **Targets and Modes are strictly mutually exclusive per step.**

1. **Target Selection (`has_targets: true`)**
   - **Semantics**: Deployment infrastructure / location variants (e.g. `docker_deploy` step running locally vs remote SSH host).
   - **Identification**: `step.has_targets == true`, `step.targets` lists available targets (`id`, `name`, `type: "local" | "remote"`).
   - **Parameters Schema**: `step.parameters` is a dictionary keyed by target ID: `parameters[<target_id>]`.
   - **Connection Specification**: Pass `target: "<target_id>"` and `target_type: "<local|remote>"`.
     - In `-i`: `-i <step_id>.target=<target_id> -i <step_id>.target_type=<local|remote>`
     - In `inputs.yaml` or `body.json`: `"target": "<target_id>"`, `"target_type": "<local|remote>"`
   - **Docker Host Rules**: For a `docker_deploy` step, copy target `type` into `target_type` (`local` or `remote`). Linux local and remote targets may declare `auto_install_docker`. Windows native local Docker is unsupported (use a Linux Docker host over SSH). macOS local Docker requires Docker Desktop running first.

2. **Mode Selection (`has_modes: true`)**
   - **Semantics**: Hardware model or application configuration variants for the same logical step (e.g. `recamera_sg2002` vs `recamera_pro`, or standard sensor vs pro model).
   - **Identification**: `step.has_modes == true`, `step.modes` lists available modes:
     - `id`: Mode identifier (e.g. `"recamera_sg2002"`, `"recamera_pro"`).
     - `name`: Human-readable label (e.g. `"reCamera (SG2002)"`, `"reCamera Pro (RV1126B)"`).
     - `default`: Boolean indicating whether this is the default mode.
     - `type`: Effective deployer type for this mode (e.g. `"recamera_console_app"`, `"recamera_pro_app"`).
     - `description`: Explanation of what this mode configures.
   - **Parameters Schema**: `step.parameters` is a dictionary keyed by mode ID: `parameters[<mode_id>]`. Each mode defines its own distinct parameters.
   - **Connection Specification**: Pass `mode: "<mode_id>"`.
     - In `-i`: `-i <step_id>.mode=<mode_id>`
     - In `inputs.yaml` or `body.json`: `"mode": "<mode_id>"`
   - **Agent Protocol for Modes**:
     - `request_template.device_connections[<step_id>]` is pre-populated with the default mode (`default: true`) and its default parameters.
     - If the user's intent or hardware matches the default mode, keep `mode: "<default_mode_id>"` and fill the parameters listed under `step.parameters[<default_mode_id>]`.
     - If the user specifies or owns a non-default hardware variant (e.g. "I have a reCamera Pro"):
       1. Set `<step_id>.mode = "<mode_id>"` (e.g. `recamera_pro`).
       2. Look up required parameters exclusively in `step.parameters[<mode_id>]` (or inspect the conditional schema via `sensecraft-engine schema <id>`).
       3. **Zero Cross-Mode Mixing**: Never pass parameters belonging to other modes. The engine strictly validates mode parameters and rejects foreign parameters with: `Parameter '<param>' in step '<step>' is not valid for mode '<selected_mode>' (it is defined in mode '<other_mode>').`
     - If the hardware model is ambiguous from context, present the choices from `step.modes` to the user before proceeding.

3. **Standard Step (neither targets nor modes)**
   - `has_targets == false` and `has_modes == false`.
   - `step.parameters` is a flat list of parameter objects for that step. No `target` or `mode` selector is needed.

## 3. Fill in and confirm (Zero-Plaintext-Password Protocol)

> [!IMPORTANT]
> **严禁在会话中索要、输出或接收用户的明文 SSH 密码！**（会触发主流大模型安全拒答拦截，且存在凭证泄露与历史污染风险）。
> - **标准且唯一支持认证方式**：采用 SSH 密钥免密认证 (`key_file: "~/.ssh/id_ed25519"` 或 `~/.ssh/id_rsa`)。
> - **若用户设备尚未配置免密公钥**：引导用户在其**本地终端**执行一次免密分发：
>   ```bash
>   ssh-copy-id -i ~/.ssh/id_ed25519.pub <user>@<device_ip>
>   ```
>   *(若本地尚无 Ed25519 密钥对，先执行 `ssh-keygen -t ed25519 -N ""` 一键创建)*。
>   输入密码的交互在用户独立本地终端完成，密码绝不流经大模型上下文，亦不留在会话与历史中。
> - **部署参数统一使用 `key_file`**：SenseCraft Engine 的部署请求格式要求远程目标通过 `key_file` 进行连接。严禁在聊天框索取明文密码。

### Method A: Direct Input Flags / Inputs File (Recommended for Agents with Engine >= 0.0.6)

Use `--input` (`-i`) to specify parameters directly without writing temporary files (requires `sensecraft-engine >= 0.0.6`; on earlier engine versions, use **Method B: Full Request Document (`--params`)** below):

```bash
# Direct step-scoped parameters (infrastructure target example):
sensecraft-engine deploy <id> \
  -i <step_id>.target=remote \
  -i <step_id>.target_type=remote \
  -i <step_id>.host=192.168.1.50 \
  -i <step_id>.username=root \
  -i <step_id>.key_file=~/.ssh/id_ed25519 \
  --replace-existing \
  --yes

# Direct step-scoped parameters (hardware mode example, e.g. reCamera Pro):
sensecraft-engine deploy recamera_ecosystem \
  --preset object_detection \
  -i obj_install_app.mode=recamera_pro \
  -i obj_install_app.host=192.168.42.1 \
  -i obj_install_app.key_file=~/.ssh/id_ed25519 \
  -i obj_install_app.device_name=recamera_front \
  --replace-existing \
  --yes
```

Or pass a YAML/JSON configuration file via `--inputs-file`:

```bash
sensecraft-engine deploy <id> --inputs-file ./inputs.yaml --replace-existing --yes
```

Where `inputs.yaml` has step-scoped values:
```yaml
# Step with target selection:
deploy_container:
  target: remote
  target_type: remote
  host: 192.168.1.50
  username: root
  key_file: ~/.ssh/id_ed25519

# Step with hardware mode selection:
obj_install_app:
  mode: recamera_pro
  host: 192.168.42.1
  key_file: ~/.ssh/id_ed25519
  device_name: recamera_front
```

> [!TIP]
> **Updating Existing Deployments**: When modifying parameters of an already deployed solution, `--replace-existing` automatically stops and replaces conflicting containers with the updated parameters and restarts them.

### Method B: Full Request Document (Legacy `--params`)

Write the completed request to `./.sensecraft-work/body.json`, keeping credentials out of the command line:

```json
{
  "solution_id": "<id>",
  "preset_id": "<preset>",
  "selected_devices": ["step_with_target", "step_with_mode"],
  "device_connections": {
    "step_with_target": {
      "target": "<target_id>",
      "target_type": "remote",
      "host": "192.168.1.50",
      "username": "<user>",
      "key_file": "~/.ssh/id_ed25519"
    },
    "step_with_mode": {
      "mode": "recamera_pro",
      "host": "192.168.42.1",
      "username": "root",
      "key_file": "~/.ssh/id_ed25519",
      "device_name": "recamera_front"
    }
  }
}
```

Remote SSH uses a regular key under `~/.ssh` or the Engine data directory (`id_ed25519` / `id_rsa`). Serial steps need both `port` and `serial_port` when the template contains both. Add `auto_replace_containers: true` only after the user agrees to replace existing containers.

Before a remote deployment, run the no-change validation:

```bash
# Validate direct input parameters:
sensecraft-engine validate <id> -i <step_id>.host=192.168.1.50 -i <step_id>.key_file=~/.ssh/id_ed25519

# Validate with specific hardware mode:
sensecraft-engine validate recamera_ecosystem --preset object_detection -i obj_install_app.mode=recamera_pro -i obj_install_app.host=192.168.42.1

# Or validate request body:
sensecraft-engine validate --params ./.sensecraft-work/body.json
```

Read `side_effects` and report any `sudo`, Docker daemon configuration or restart, package install, system configuration, reboot, firmware flash, or local script operation. Stop for user approval if a listed effect is outside the agreed scope. Save `/etc/docker/daemon.json` before a remote deployment when it exists so a later restoration can be reviewed separately.

## 4. Start and follow

```bash
sensecraft-engine deploy --params ./.sensecraft-work/body.json --yes --detach --lang zh
sensecraft-engine status <deployment-id> --json
sensecraft-engine logs <deployment-id> --since <N>
```

Keep the returned `deployment_id`. Poll `status` until it is `completed`, `failed`, `cancelled`, or `interrupted`; read `logs` with the last event sequence. `--follow` can stream logs when the command timeout allows it. A request error (exit 2) needs corrected fields; a busy device (exit 3/409) needs the other deployment resolved first.

Without `--detach`, `deploy --json` waits for the final result. Interrupting the client only detaches from the running Engine deployment; continue with `status` and `logs`.

## 5. Verify

`completed` is not by itself service verification. Handle every `verify_required` event with `verify.md`, then check the target:

- Docker services remain `running` and healthy. Use `sensecraft-engine docker ps --json` locally or the remote form documented by the Engine help.
- Service endpoints return the expected 2xx/3xx response.
- For services with a health check, check once more after about 60 seconds and inspect restart counts for a crash loop.

Report the URL, device, deployed solution, and verification evidence. Do not report success when a container restarts, disappears, or its endpoint stops answering.

### IoT End-to-End Verification Pipeline (Hardware Flashing to Closed Loop)

For solutions combining microcontroller hardware with smart home / IoT integration (e.g. ESP32 panels with Home Assistant):

```
Flashed (固件写入完成)
  ↳ Provisioned (Wi-Fi 凭据注入，获取局域网 IP)
    ↳ Entry Verified (HA 中存在本面板 entry 且 loaded)
      ↳ Entity Bound (目标灯写入 text 实体，允许执行动作开启)
        ↳ Touch Verified (捕获物理触控导致的灯具状态变化)
```

1. **Flashed**: Core firmware successfully flashed and verified via post-flash reboot.
2. **Provisioned (Improv Serial Wi-Fi Setup)**:
   - For devices running Improv Serial over USB UART (115200 baud), prompt and guide the user through serial Wi-Fi provisioning to inject 2.4 GHz credentials without manual configuration files.
   - Alternatively, connect via the device's Captive Portal hotspot if serial provisioning is unavailable. Confirm the device connects to the local network and acquires a valid LAN IP.
3. **Entry Verified (Unique Identity Matching)**:
   - Confirm the device integration entry exists in Home Assistant and is in the `loaded` state.
   - **Device Uniqueness Principle**: In multi-device local networks, match devices strictly by unique MAC address or assigned IP address, avoiding misconfiguration across multiple ESPHome nodes sharing similar default names.
4. **Entity Bound (Two-Step Action Binding)**:
   - Enable "Allow the device to perform Home Assistant actions" under the device's integration options.
   - Write the target light entity ID (e.g. `light.living_room`) to the designated configuration entity (`text.e1003_target_light`). Native API actions eliminate the need for manual Home Assistant Automation rules.
5. **Touch Verified (Physical Closed Loop)**:
   - Instruct the user to physically tap on-device touch zones (toggle button, brightness steps: 25%, 50%, 75%, 100%).
   - Verify that the target light entity state and brightness update accordingly in Home Assistant.

## 6. If anything failed

Go to `diagnose.md` with the `deployment_id`. Retry only after reading the error. Transient registry or network errors may be retried up to five times with increasing waits; deterministic credential, parameter, disk, port, or container errors require a fix before retry and at most three rounds.

To retry a partial deployment, reuse the same request body and list only failed devices. Do not change the preset or target values while diagnosing a failure. Keep the body file private and remove `./.sensecraft-work/` after the deployment workflow completes.

## Cancel

Only after the user approves cancellation:

```bash
sensecraft-engine cancel <deployment-id>
sensecraft-engine status <deployment-id> --json
```

Wait for `cancelled` and report which steps had already run; a cancelled deployment may leave a device partially configured.

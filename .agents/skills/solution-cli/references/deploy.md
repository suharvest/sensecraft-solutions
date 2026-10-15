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

## 2. Read what the deployment needs

```bash
sensecraft-engine deploy-info <id> --lang zh
sensecraft-engine doctor --json
sensecraft-engine device ports
sensecraft-engine device scan --timeout 5
```

Read `presets[]`, `steps[]`, `device_connections`, `selected_devices`, and `request_template` from `deploy-info`. A preset with more than one variant requires the user's choice. Fill every `<REQUIRED: ...>` value from the user or a read-only device check; never invent device IDs, connection keys, SSH credentials, serial ports, or Docker targets.

For a `docker_deploy` step, use the target listed by `deploy-info` and copy its `type` into `target_type` (`local` or `remote`). Linux local and remote targets may declare `auto_install_docker`; the engine can install Docker/Compose when that option is enabled, but offline installation requires matching packages to be obtainable and usable permissions to already exist. Windows native local Docker is unsupported; use a Linux Docker host over SSH. macOS local Docker requires the user to install and start Docker Desktop first. The CLI does not install Docker Desktop or silently obtain `sudo`.

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

Write the completed request to `./.sensecraft-work/body.json`, keeping credentials out of the command line:

```json
{
  "solution_id": "<id>",
  "preset_id": "<preset>",
  "selected_devices": ["<step_id>"],
  "device_connections": {
    "<step_id>": {
      "target": "<target_id>",
      "target_type": "remote",
      "host": "192.168.1.50",
      "username": "<user>",
      "key_file": "~/.ssh/id_ed25519"
    }
  }
}
```

Remote SSH uses a regular key under `~/.ssh` or the Engine data directory (`id_ed25519` / `id_rsa`). Serial steps need both `port` and `serial_port` when the template contains both. Add `auto_replace_containers: true` only after the user agrees to replace existing containers.

Before a remote deployment, run the no-change validation:

```bash
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

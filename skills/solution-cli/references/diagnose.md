# Diagnose a failed or misbehaving deployment

Follow the rules in `SKILL.md` (what needs the user's OK, at most 3 rounds).
If the user runs the desktop app and deployed from it, `app-only.md` §3 covers
the app's own deployment list and logs.

## 1. Find the deployment

If you started it, you already have the `deployment_id`. Otherwise:

```
sensecraft-engine api GET "/api/deployments?limit=20"   # newest first: id, solution_id, status
```

## 2. Collect evidence

Start with the status. **The real error is usually in the failing step's
`message`** (`devices[].steps[]` with `status: failed`); top-level errors may
only say "Device X deployment failed".

```
sensecraft-engine status <deployment_id> --json
sensecraft-engine api GET /api/deployments/<deployment_id>/summary
```

Then the error-level events, and the full log of the failing device:

```
sensecraft-engine logs <deployment_id>                 # NDJSON; look at type=log, level=error
sensecraft-engine api GET "/api/deployments/<deployment_id>/logs?device_id=<device_id>&limit=300"
```

If the logs are empty or end abruptly (status `interrupted`: the engine
instance stopped during the deployment), read the engine log
`~/.sensecraft/logs/engine.log` (Windows: `%USERPROFILE%\.sensecraft\logs\engine.log`),
last ~200 lines. `sensecraft-engine daemon status` prints JSON (`--json` is
accepted and changes nothing; exit 1 with `"running": false` when no instance
is running). A running instance shows `busy` (a deployment is running),
`python_backend` (null: no desktop-app backend involved) and
`python_supervisor.state`.

Note the failing device, step and the first error — later errors are usually
consequences of the first.

## 3. Check the device (read-only, no need to ask)

Which containers belong to the solution: in the solution folder
(`~/.sensecraft/content/solutions/<id>/`) the step's `devices/<x>.yaml` names
the compose file (`docker.compose_file`) and project
(`docker.options.project_name`); the compose file may set `container_name`.

Through the engine (no separate SSH client needed):

```
SC_SSH_PASSWORD=<password> sensecraft-engine docker ps --host <ip> --username <user> --json
SC_SSH_PASSWORD=<password> sensecraft-engine docker logs <container> --host <ip> --username <user> --tail 100
# SSH key (engines with --key-file; older engines accept a password only):
sensecraft-engine docker ps --host <ip> --username <user> --key-file ~/.ssh/id_ed25519 --json
```

Omit `--host` for this computer's Docker. With an SSH client, the same
read-only commands as before:

```
docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker logs --tail 100 <container>
df -h /
ss -ltnp            # who holds a port (use: sudo ss -ltnp if names are hidden)
ping -c 2 8.8.8.8   # internet reachability
```

For local targets and USB devices also run `sensecraft-engine doctor --json`
(serial permission, Docker, disk, network) and
`sensecraft-engine device ports` (is the USB device visible).

## 4. Classify, then act

Match the evidence against `error-catalog.md`. Every problem falls in one of
three classes:

| Class | Example | What you do |
|---|---|---|
| **Device / environment** | port taken, disk full, Docker missing, network blocked, wrong password, serial permission | Propose the exact fix commands → user OK → run them → retry |
| **Solution configuration** | timeout too short, wrong port/env in compose, health check endpoint 404, minor syntax/transfer glitch | **CLI / Engine mode (Auto-healing patch)**: Copy the solution from `~/.sensecraft/content/solutions/<id>` to `./.sensecraft-work/solutions/<id>`, apply the minimal required fix, and redeploy with `sensecraft-engine deploy --params <params-file> --solutions-dir ./.sensecraft-work/solutions --yes --detach` (preserving parameters, restricted to failed devices) so the user succeeds immediately! Show the user the patch diff. Desktop app running: fix it in the edit copy (`app-only.md` §4) → validate → apply → retry. |
| **Engine bug** | exit code 5, a panic in `engine.log`, a step that fails the same way on any device, behaviour contradicting the solution's own config | Stop. Prepare the issue report below |

If the evidence does not fit any row, say so and show the user the first error
with your best hypothesis and what would confirm it. Do not guess-and-retry.

## 5. Retry

Restart only the failed device (`selected_devices` = that device, see
`deploy.md` §6). First retry without asking; later ones need the user's OK.
After 3 rounds without success, stop and report.

## 6. Report

Always finish with: what failed, the evidence (first error line), what you
changed (commands run, files edited with a diff), and the result.

### Engine bug: issue report

Engine bugs are reported on the public repository
`suharvest/sensecraft-solutions` with the **App / engine bug** form; the
maintainers move them on from there. Do not submit it yourself — give the user
a link to open in the browser and submit with their own GitHub account.

1. Fill these fields (passwords, tokens and IP addresses removed):

   | Field id | Content |
   |---|---|
   | `title` | `[engine] <step type> fails: <first error, one line>` |
   | `app_version` | `engine <version>` from `sensecraft-engine --version` (or the app's version when deployed from the app) |
   | `os` | this computer's OS and version |
   | `device` | target device model, OS, CPU architecture (or "this computer (local Docker)") |
   | `solution` | `<solution_id> / <preset_id> / <step id> (<type>)` |
   | `edited` | `No` or `Yes (diff below)` |
   | `what_happened` | first error and the 10–20 log lines around it |
   | `reproduce` | numbered steps (the `sensecraft-engine` commands, password removed) |
   | `ruled_out` | device checks that passed |
   | `diff` | the edit copy's diff (`app-only.md` §4.5), only if edited |

2. Build the link, URL-encoding every value:

   ```
   https://github.com/suharvest/sensecraft-solutions/issues/new?template=engine-bug.yml&title=<...>&app_version=<...>&os=<...>&device=<...>&solution=<...>&edited=<...>&what_happened=<...>&reproduce=<...>&ruled_out=<...>
   ```

   Keep the link under about 7,000 characters: if the log excerpt or diff is
   longer, leave those fields out of the link and give the user that text
   separately to paste into the form.
3. Show the user the filled fields and the link, and say the report will be
   public.

---

## 7. 本地自动打补丁 (Auto-patching) 成功后的脱敏建议回流

当通过 `./.sensecraft-work/solutions/<id>` 本地修复（如解决健康检查超时、 Compose 端口冲突或环境变量微调）并最终验证成功后，Agent **必须主动询问用户是否将脱敏修复 Diff 反馈给 Seeed 官方工程团队**，以实现官方方案库的持续演进：

1. **主动交互询问**：
   > *“💡 提示：本次部署通过本地热补丁修复了官方方案配置中的轻微缺陷，当前系统已稳定运行。是否同意将已脱敏的修复 Diff 生成建议提交给 Seeed 官方团队？[生成提交链接 / 忽略]”*
2. **生成预填充建议链接**：
   若用户同意，生成带脱敏 Diff 的官方 GitHub 方案优化建议链接（已去除所有局域网 IP、密码、密钥和私有路径）：
   ```
   https://github.com/suharvest/sensecraft-solutions/issues/new?template=solution-enhancement.yml&title=%5BPatch%5D+<solution_id>+configuration+fix&solution=<solution_id>&diff=<encoded_sanitized_diff>
   ```
   用户一键即可直达提交，完成从“端侧自愈”到“云端反哺”的商业与技术生态闭环。

# AGENTS.md — Working Guide for AI Agents Assisting SenseCraft Solution Users

This document is for **AI agents** (Claude Code and similar assistants). It defines the standard workflows an agent should follow when helping different kinds of SenseCraft Solution users.

This open-source repository contains the **solution content** (YAML / Markdown / assets) and the **authoring & validation tooling** (`spec/`, `packages/`, `skills/`). The deployment engine itself (the desktop app / headless binary) is distributed separately as the **SenseCraft Solution app**. The workflows below assume the user already has that app (or the `provisioning-station` engine binary) installed.

## Four user roles, four workflows

| Part | User role | Typical need | Key artifact |
|---|---|---|---|
| **A** | Non-technical user (operations, AE, marketing) | Edit copy, add images, tweak intro/guide, then **preview** in the app | Solution import API (preview flow) |
| **C** | End user with the app installed | "One-click deploy a solution" | HTTP API `/api/solutions/*` boost flow |
| **D** | DevOps / CI / scripted | Headless batch deploy, CI automation, single-device debugging | **`solutionctl` CLI** (`solutionctl deploy …`) + **headless engine binary** (`provisioning-station serve --headless`) |
| **E** | DevOps / agent operating deployed devices | List deployed apps, start/stop/update, firmware OTA, factory restore, content updates, Docker ops | **headless engine binary** `serve --headless` + device-management endpoints |

> Note: a fifth role — second-development of the engine itself (adding deployers / frontend handlers / plugins) — lives in the closed-source engine repository and is intentionally out of scope here.

The agent should **identify the user role first, then pick the Part** — don't mix them.

## Available skills

Detailed, loadable playbooks live under `skills/<name>/SKILL.md`. **Claude Code**
auto-discovers them via the `.claude/skills` symlink (just clone and they appear).
**Other agents (e.g. Codex)** should read the relevant `SKILL.md` directly. Load
a skill when its job comes up:

| Skill | Load it when… |
|---|---|
| `solution-cli` | Driving the engine from the command line / CI — `solutionctl` for deploy, validate, discover solutions, device ops (Part D). |
| `deploy-solution` | Deploying via the running backend's REST API (Part C boost flow). |
| `author-solution` | Creating a new solution from source material (reproduce → validate → document). |
| `solution-copywriting` | Polishing a solution's intro / guide copy. |
| `preview-solution-content` | Previewing locally-edited content in the installed app (Part A). |
| `prepare-docker-images` / `prepare-deb-package` / `prepare-esp32-firmware` / `prepare-himax-firmware` / `prepare-recamera-nodered` | Preparing the deploy artifacts for the matching deployer type. |
| `integrate-jetson-solution` | Building a Jetson `docker_remote` solution package. |

> Windows note: the `.claude/skills` symlink needs `git config core.symlinks true`
> (and Developer Mode) to clone as a real link; otherwise point your agent at
> `skills/` directly.

---

# Part A — Assisting non-technical users: edit copy / preview

**Typical triggers:**
> "I edited `solutions/foo/description_zh.md`, how do I see it in the app?"
> "Preview this solution locally"
> "Import this change into the app to check the result"

## Set boundaries first

This flow is a **local preview**, not a release. Changes land only on the current machine's app. It will **not**:
- Trigger an OTA push to all users
- Change `bundled_hashes.json`
- Trigger any git operation

If the user actually wants "everyone to see it" — stop. That is a separate release flow that runs `scripts/generate_solution_manifest.py` and commits `bundled_hashes.json`, and requires explicit confirmation.

## Standard flow

Invoke the skill `preview-solution-content`. Full steps:

1. **Ask for the port** (every time — don't guess).
   Guide the user to open **Settings → API Access** in the app and copy the port number from the "interface address". The "enable LAN API access" toggle is **not** needed — local requests are auth-free.

2. **Health check**
   ```bash
   BASE=http://127.0.0.1:<port>
   curl -fsS "$BASE/api/health"
   ```

3. **Package the solution** into a zip whose root contains `solution.yaml` (compatible with the import API). The `solutionctl` CLI or the app's own export feature can produce this; skip system junk like `.DS_Store`.

4. **parse → apply**
   ```bash
   ZIP="$(pwd)/<id>.zip"
   PARSE=$(curl -fsS -X POST "$BASE/api/solutions/import/parse" -F "file=@$ZIP")
   TEMP_ID=$(echo "$PARSE" | jq -r .temp_id)
   curl -fsS -X POST "$BASE/api/solutions/import/apply" \
     -H "Content-Type: application/json" \
     -d "{\"temp_id\":\"$TEMP_ID\",\"id\":\"<id>\",\"conflict_resolution\":\"overwrite\"}"
   ```

5. **Have the user verify**: refresh the solution list / detail page in the app.

## Common pitfalls

- Wrong port → `Failed to connect`. Have the user recheck Settings.
- `parse` 400 "missing solution.yaml" → the user broke `solution.yaml`; tell them to `git diff`.
- Change not showing → frontend cache; have the user hard-refresh or restart the app.
- Multiple solutions edited at once → do them one at a time, never batch silently.

---

# Part C — AI-driven deployment (boost flow)

This Part tells an AI agent how to drive a **one-shot deployment ("boost")** of a solution through the SenseCraft Solution app's HTTP backend, after the app has been installed on the user's machine.

Scope: just the boost flow — discover solutions, resolve required inputs, start deployment, monitor to completion, report result. For the full API surface (device management, Docker ops, live streams, etc.) consult the app's API documentation.

---

## 1. Connect to the backend

The app ships a local FastAPI backend. Base URL depends on how the app is running:

| Environment | Base URL |
|---|---|
| Desktop app (installed) | `http://127.0.0.1:{port}/api` — port is dynamic |
| dev mode | `http://localhost:3260/api` |

### Getting the port in the desktop app

The host picks a free port at launch. Two ways to discover it:

1. **From inside the WebView** (preferred if you run as a page script): read `window.__BACKEND_PORT__`.
2. **From outside** (external agent process): probe `http://127.0.0.1:{p}/api/health` on common ports, or ask the user to click *Settings → About → Backend port*.

### Auth

- Requests from `127.0.0.1` / `localhost` — **no auth needed**.
- Requests from LAN / remote (only if the user enabled `PS_API_ENABLED=true`) — need `X-API-Key: <key>` header. Create a key via `POST /api/keys {"name": "my-agent"}` from a localhost session first.

Sanity check before anything else:

```http
GET /api/health
```

---

## 2. The boost flow in five calls

```
┌───────────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────┐  ┌──────────┐
│ list solutions│→ │  deploy-info │→ │    start   │→ │ monitor │→ │ summary  │
└───────────────┘  └──────────────┘  └────────────┘  └─────────┘  └──────────┘
```

### Step 1 — Find the solution the user wants

```http
GET /api/solutions/?lang=en
```

Returns an array of solutions with `id`, `name`, `summary`, `category`, `tags`, `solution_type`. Pick the `id` that matches the user's intent (fuzzy match on `name` / `summary` / `tags`; ask the user if multiple plausible matches).

Filters: `category=voice_ai`, `solution_type=...`, `include_disabled=false`.

### Step 2 — Get the ready-to-fill request template

```http
GET /api/solutions/{solution_id}/deploy-info?lang=en
```

This is the **AI-friendly endpoint**. It returns:

- `presets`: list of deployment presets. If more than one, pick one based on user intent or ask. Re-call with `?preset_id=xxx` to narrow the device list.
- `steps[]`: each step describes a device/stage —
  - `device_id`, `name`, `type` (`docker_local` / `docker_remote` / `esp32_usb` / `himax_xmodem` / `script` / `manual` / …)
  - `connection_type` (`local` / `ssh` / `serial` / `none`)
  - `parameters[]`: each has `key`, `label`, `type`, `required`, `default`, `options` (for select), `description`
  - `targets[]` + `parameters` keyed by target (when the step supports variants, e.g. local-vs-remote)
- `request_template`: **a pre-filled JSON body** for `POST /api/deployments/start` with every known default. Your job is to fill in the blanks the user still needs to provide.

### Step 3 — Resolve user inputs

Walk `request_template.device_connections`. For each device:

1. If the field already has a non-empty value (default), keep it.
2. If it's blank and `required`, you must get it from the user. Typical inputs:
   - SSH devices → `host`, `port` (default 22), `username`, `password` or `private_key`
   - Serial devices → `port` (get candidates from `GET /api/devices/ports`)
   - App-specific → anything declared in `parameters`
3. Optional: validate SSH reachability first with `POST /api/devices/test-connection` before starting — fails fast without creating a deployment record.

Device auto-detection shortcut: `GET /api/devices/detect/{solution_id}?lang=en` may pre-fill obvious things (local Docker reachable? serial port plugged in? mDNS hit?).

### Step 4 — Start the deployment

```http
POST /api/deployments/start
Content-Type: application/json

{
  "solution_id": "...",
  "preset_id": "...",              // if presets exist
  "selected_devices": ["step1", "step2", ...],
  "device_connections": { ...filled template... }
}
```

Returns `{"deployment_id": "...", "status": "running"}`. Keep the `deployment_id`.

> Dry-run first (recommended for untrusted inputs): `POST /api/deployments/validate` with the same body — returns validation errors without side effects.

### Step 5 — Monitor to completion

Poll every ~2 seconds until `status` is terminal (`completed` / `failed` / `cancelled`):

```http
GET /api/deployments/{deployment_id}
```

Returns `overall_progress` (0–100), per-device `status` + `current_step`, and step-level progress. **Do not fetch logs every tick** — it wastes context.

When it's done (or if `status == "failed"`), get the compact result:

```http
GET /api/deployments/{deployment_id}/summary
```

Returns errors, warnings, duration. ~1KB. Show this to the user.

Only if `summary` shows errors worth diagnosing, pull filtered logs:

```http
GET /api/deployments/{deployment_id}/logs?level=error,warning&limit=20
```

User wants to abort? `POST /api/deployments/{deployment_id}/cancel`.

---

## 3. Minimal pseudo-code

```python
BASE = f"http://127.0.0.1:{port}/api"

# 1. pick solution
sid = choose(GET(f"{BASE}/solutions/?lang=en"), user_intent)

# 2. fetch template
info = GET(f"{BASE}/solutions/{sid}/deploy-info?lang=en")
preset = pick_preset(info["presets"], user_intent)  # may re-GET with ?preset_id=
body  = info["request_template"]

# 3. fill required blanks by prompting user
for dev_id, conn in body["device_connections"].items():
    for step in info["steps"]:
        if step["device_id"] != dev_id: continue
        for p in flatten_params(step):
            if p["required"] and not conn.get(p["key"]):
                conn[p["key"]] = ask_user(p["label"], p.get("description"))

# 4. start
dep = POST(f"{BASE}/deployments/start", json=body)
dep_id = dep["deployment_id"]

# 5. monitor
while True:
    s = GET(f"{BASE}/deployments/{dep_id}")
    report_progress(s["overall_progress"], s.get("current_step"))
    if s["status"] in ("completed","failed","cancelled"): break
    sleep(2)

# 6. report
summary = GET(f"{BASE}/deployments/{dep_id}/summary")
if s["status"] != "completed":
    logs = GET(f"{BASE}/deployments/{dep_id}/logs?level=error,warning&limit=20")
    explain(summary, logs)
else:
    celebrate(summary)
```

---

## 4. Rules of good behavior

- **Never invent field values.** If a `required` input is missing, ask the user. SSH passwords and hosts in particular — do not guess.
- **Never parse logs as the primary progress signal.** Use `GET /api/deployments/{id}` for status; logs are only for diagnosis after a failure.
- **Respect context budget.** Start with `/deploy-info` and `/summary` (small); only drill into `/logs` on failure.
- **Confirm before cancelling** an in-flight deployment — it may leave partial state on devices.
- **Confirm before destructive reinstalls.** If the same solution is already running (`GET /api/device-management/active`), ask whether to update-in-place (`POST /api/docker-devices/.../upgrade`) or redeploy from scratch.
- **Language.** Pass `lang=zh` everywhere if the user speaks Chinese — response `name`/`label`/`description` will be localized.

---

# Part D — Assisting DevOps / CI / scripted deployment: the engine CLI

**Typical triggers:**
> "Batch-deploy solution X to these 5 Jetsons"
> "Run a remote deployment in GitHub Actions"
> "No app installed on this machine, can I deploy from the command line?"
> "Debug a single device without clicking through the UI"

## Set boundaries first

The headless engine shares the desktop app's deployment code. One-shot deployment (usage ①) covers **deployment-related** capabilities only; `serve --headless` (usage ②) additionally exposes the **full device-management surface** (see Part E). It does **not** do:
- Content editing (use Part A)
- Engine / plugin development (lives in the closed-source engine repo)
- UI-type steps (web dashboard, voice chat, image preview, etc.) — these are lazy-skipped in one-shot deployment with a prompt to use the desktop app

If the user's need exceeds deployment / device operations, stop and guide them to the right Part.

## Two usages

Drive the engine through **`solutionctl`** — the thin CLI client in `packages/solutionctl/`. **`solutionctl` auto-locates the engine binary** (env `$SENSECRAFT_ENGINE_BIN` → `~/.sensecraft/engine.json` handshake → platform-native lookup), so the agent never needs to know the binary's path. Calling the bare `provisioning-station <cmd>` directly still works if you already know the path, but `solutionctl` is recommended.

The engine has two GUI-less usages:

| Usage | Command | Good for |
|---|---|---|
| ① One-shot in-process deploy | `solutionctl deploy <id> --connection '<json>' --json [--skip-verify]` | CI, batch deploy, run-once-and-exit |
| ② Headless REST service | `provisioning-station serve --headless` (or `solutionctl manage`, which internally starts `serve --headless`) then hit endpoints | Full device management (start/stop/update/OTA/restore/…), see **Part E** |

## Usage ① — One-shot in-process deploy

### 1. Locate solution + pick preset/device

```bash
solutionctl solution list
solutionctl solution show <solution_id> [--lang en|zh]
```

`solution show` lists every preset and each preset's steps + associated device YAML. **Look before you choose** — don't guess preset names.

UI-only steps (`web_dashboard` / `image_predict` / `voice_chat`, etc.) are lazy-skipped when run headless; this doesn't affect other steps' deployment, but the user won't get the UI — tell them those steps need the desktop app.

### 2. Build the `--connection` JSON

Format: `{device_id: {host, username, password, port, target, target_type, ...}}`

Note it is a **nested** dict, not flat. `device_id` must match what `solution show` shows. `target` / `target_type` come from the device YAML's `target:` field (only needed for multi-target solutions).

**Never** invent credentials. Have the user provide them. SSH passwords must always be asked for; redact them as `<REDACTED>` in logs/examples.

### 3. Run the deployment

```bash
solutionctl deploy <solution_id> \
    --preset <preset_id> \
    --device <device_id> \
    --connection '<json>' \
    --json \
    --replace-existing \
    --yes
```

Key flags:
- `--json` emits an NDJSON event stream (one JSON event per line), machine-parseable; prints a structured result dict at the end then exits by success/failure
- `--device` omitted = deploy all steps of the preset (CI scenario); specified = single-step debugging
- `--skip-verify` skips verify-category interactive steps (for unattended CI)
- `--replace-existing` auto stop + replace when a same-named container already exists on the remote (default behavior fails and asks the user to confirm)
- `--yes` / `-y` skips confirmation prompts (required for CI)
- `--solutions-dir` when the solutions tree is not in the default location

### 4. Interpret the result

Process exit code 0 = success, non-zero = failure; the last line prints a result dict (`status` + per-device `steps`).

- `status: completed/success` + `docker ps` shows container `(healthy)` → real success
- Failure but the container is actually `Up X seconds (healthy)` → most likely a healthcheck config bug (e.g. probing an auth endpoint that returns 401), **not** a deployment failure — check the compose file's `healthcheck:` section
- Error contains `Found existing containers: ...` → tell the user to re-run with `--replace-existing`
- Any raw 60-line traceback → engine bug, have the user file an issue upstream

### CI example

```yaml
# .github/workflows/deploy.yml
- name: Deploy to staging
  env:
    DEPLOY_PWD: ${{ secrets.JETSON_PWD }}
  run: |
    solutionctl deploy smart_warehouse \
      --preset sensecraft_cloud --device warehouse \
      --connection "{\"warehouse\":{\"host\":\"$JETSON_HOST\",\"username\":\"jetson\",\"password\":\"$DEPLOY_PWD\",\"port\":22,\"target\":\"warehouse_remote\",\"target_type\":\"remote\"}}" \
      --json --skip-verify --replace-existing --yes
```

## Usage ② — Headless REST service

```bash
provisioning-station serve --headless
# or: solutionctl manage   # internally starts `serve --headless`
```

- Binds `127.0.0.1`; auto-selects a free port if `--port` is not given.
- **Before** starting, prints a machine-readable ready signal (json) to stdout — capture it to get `base_url`:
  ```json
  {"status":"serving","port":50362,"pid":42574,"base_url":"http://127.0.0.1:50362"}
  ```
- Local requests are auth-free (middleware allows `127.0.0.1`); not exposed to the LAN.
- Then hit REST endpoints for deployment (same boost flow as Part C) or device operations (see **Part E**).

## Rules of good behavior

- **Never leak credentials in output/logs**; replace passwords with `<REDACTED>` in examples. SSH passwords must be asked for, never invented.
- **`--replace-existing` / `update` / `restore` are destructive**: they stop running remote containers / pull new images and restart / factory-reset. **Confirm with the user** before using them in production.
- **In CI, inspect the error type before reporting**: a readable business error (healthcheck 401, config error) ≠ an engine bug. The former is a config fix, the latter warrants an upstream issue.
- **Headless shares deployment code with the desktop app** — a deploy that passes headless also passes in the app, and vice versa. Use this to judge bug ownership.

---

# Part E — Device operations (headless)

**Typical triggers:**
> "Show what solutions are running on this Jetson"
> "Restart / stop that container"
> "Upgrade the reCamera firmware"
> "Factory-reset this device"
> "Pull the latest solution content update"

## Prerequisite

First start `serve --headless` per **Part D usage ②** to get `base_url` (or reuse the port of an already-running desktop app, see Part C §1). All calls below are `$base_url + <endpoint>`. Local requests are auth-free; passwords for remote SSH operations must be **requested from the user**.

## Operation → endpoint quick reference

| Capability | Endpoint | Notes |
|---|---|---|
| List deployed apps (get host/port/device_id) | `GET /api/device-management/active` | optional `?solution_id=` filter; returns `deployment_id` / `solution_id` / `device_id` / `host` / `app_url` / `status` |
| App start/stop/restart/update | `POST /api/device-management/{deployment_id}/action` | body `{"action":"start\|stop\|restart\|update","password":"<REDACTED>"}`; remote needs SSH password |
| App update (pull new image + restart, local/remote) | `POST /api/device-management/{deployment_id}/update` | body `{"password":"<REDACTED>"}` (remote only) |
| Remote container full upgrade (pull new image + recreate) | `POST /api/docker-devices/upgrade` | body `{host,port,username,password,container_name,compose_path,project_name?}` |
| reCamera firmware OTA (start) | `POST /api/firmware/start` | body `{"device_type":"recamera","connection":{"host","password",...},"verify_after_reboot":true,"firmware_source":"files","method":"local"}` → returns `operation_id` |
| reCamera firmware OTA (poll 8-step state machine) | `GET /api/firmware/{operation_id}/status` | returns `status`/`progress`/`current_step`/`completed_steps`/`total_steps`; an irreversible flash may need `POST /api/firmware/{op}/confirm` first |
| Factory restore (list supported devices / ports) | `GET /api/restore/devices?lang=en`, `GET /api/restore/ports` | |
| Factory restore (start) | `POST /api/restore/start` | body `{"device_type":"...","connection":{...}}` (himax_usb needs `port`, ssh_restore needs `host`+`password`) → returns `operation_id` |
| Factory restore (poll status) | `GET /api/restore/{operation_id}/status` | |
| Content/solution-package OTA (check / download) | `GET /api/content-updates/check`, `POST /api/content-updates/download/{solution_id}`, `POST /api/content-updates/download-all` | download progress `GET /api/content-updates/progress` |
| Local Docker (check / containers / actions) | `GET /api/docker-devices/local/check`, `/local/containers`, `/local/managed-apps`, `POST /local/container-action` | |
| Remote Docker (connection test / containers / actions) | `POST /api/docker-devices/connect`, `/containers`, `/managed-apps`, `/container-action?container_name=&action=` | bodies all carry SSH `{host,port,username,password}` |
| Device discovery / connection test | `GET /api/devices/scan-mdns?timeout=3`, `POST /api/devices/test-connection` | test-connection body `{host,port,username,password}` |
| Version check | `GET /api/solutions/{solution_id}/versions` | current/available version + whether an update exists |

> Long operations (firmware / restore) are **async**: `start` returns an `operation_id`, then poll `/status` until `status` is terminal. Follow the same context-budget discipline as Part C — prefer `/summary`/`/status`, only pull detailed `logs` on failure.

## Credential red lines (must follow)

- **Always ask for SSH passwords**: passwords for remote operations must always be requested from the user, **never invented**; use `<REDACTED>` in logs/examples.
- **Confirm destructive operations first**: `update` (pull new image + restart), `restore` (factory reset), `action: stop` (stop a service) must be **confirmed with the user** before execution. When `active` already shows the same solution running, clarify whether it's update-in-place or a fresh deploy.
- **Context budget**: prefer `active` / `summary` / `status` (small), only pull `logs` on failure.

# Desktop-app-only capabilities

> **Requires the SenseCraft Solution desktop app** running on this computer.
> Everything here talks to the app's local HTTP API with `curl`. The engine
> CLI path in `SKILL.md` does not need any of it. Use this file when the user
> has the app open and wants to change a solution's configuration, deployed
> from the app, or asks what the app is showing.

Sections: 1. Connect to the app · 2. Deploy through the app · 3. Diagnose
through the app · 4. Change a solution's configuration (edit copy).

> **Windows PowerShell:** `curl` there is an alias for `Invoke-WebRequest`.
> Always type `curl.exe`. Send JSON bodies from a file (`--data @body.json`)
> instead of inline strings to avoid quoting problems.

## 1. Connect to the app (every app task)

1. Read the runtime file:
   - macOS / Linux: `~/.sensecraft/runtime.json`
   - Windows: `%USERPROFILE%\.sensecraft\runtime.json`

   It holds `base_url`, `contract_version`, `logs_dir`, `solutions_dir` and
   `solutions_edits_dir`.
2. Check the app is really there: `curl -s <base_url>/api/health` must return
   `"status": "healthy"`. The file can be left over after a crash.
3. If the file is missing or the check fails, the app is not running: ask the
   user to open **SenseCraft Solution** and try again. (Developers running
   `./dev.sh` from source: `base_url` is `http://127.0.0.1:3260`.)
4. If `contract_version` is below 6, deploying and diagnosing still work, but
   config editing is not available: tell the user to update the app.
5. The `sensecraft-engine` CLI writes the same file for its own instance. A
   file with `"schema_version": 2` and `"python_backend": null` points at an
   engine instance started by the CLI, not at the app: the app is not running.

Below, `BASE` means the `base_url` value. Add `lang=zh` to API calls that take
`lang` when the user writes in Chinese, `lang=en` otherwise.

## 2. Deploy through the app

`BASE` comes from §1. Examples use `lang=en`; use `lang=zh`
for a Chinese-speaking user.

### 2.1 Find the solution

```
curl -s "BASE/api/solutions?lang=en"
```

Match the user's wording against `name` / `summary`. Confirm the `id` with the
user if more than one fits.

### 2.2 Read what the deployment needs

```
curl -s "BASE/api/solutions/<id>/deploy-info?lang=en"
```

- `presets[]` — deployment variants. If there is more than one, ask the user which
  one, then call again with `&preset_id=<preset>`.
- `steps[]` — each step's `device_id`, `type`, `required`, parameters, and for
  `docker_deploy` steps the `targets` (local = this computer's Docker, remote =
  a device over SSH).
- `request_template` — a ready request body. Values shaped like
  `<REQUIRED: ...>` must be filled in; everything else has a working default.

Never make up step or device IDs: the keys of `device_connections` and the
entries of `selected_devices` are exactly the ones in `request_template`.

Optional device discovery, to pre-fill hosts:

```
curl -s "BASE/api/devices/detect/<id>?preset=<preset>"     # USB / serial
curl -s "BASE/api/devices/scan-mdns"                        # SSH devices on the LAN
curl -s "BASE/api/docker-devices/local/check"               # local Docker
```

### 2.3 Fill in and confirm

Ask the user for every `<REQUIRED: ...>` value (device IP, username, password,
and any user inputs). For `docker_deploy` steps pick the target with
`"target": "<target id>"` **and set `"target_type"` to that target's own type**
(`local` / `remote`, from deploy-info `targets`) — or remove `target_type`. The
template carries the default target's type; leaving it while switching
`target` is rejected with a 400. Remote targets also need `host`, `username`,
`password`. Add `"auto_replace_containers": true` only if the user agrees to
replace existing containers with the same name.

Write the filled body to a file, e.g. `body.json`:

```json
{
  "solution_id": "<id>",
  "preset_id": "<preset>",
  "selected_devices": ["<step_id>"],
  "device_connections": {
    "<step_id>": {"target": "<target_id>", "host": "192.168.1.50",
                  "username": "<user>", "password": "<password>"}
  }
}
```

Show the user the body with the password as `<REDACTED>` before starting.

### 2.4 Start and wait

```
curl -s -X POST "BASE/api/deployments/start" -H "Content-Type: application/json" --data @body.json
```

Keep the returned `deployment_id`. The response also lists each device with
`status`: `deploying`, or `skipped` with a `reason` (manual / info-only steps
are always skipped — that is normal, not an error).

Poll every 3–5 seconds:

```
curl -s "BASE/api/deployments/<deployment_id>/summary"
```

`status` is `running` while in progress and ends as `completed`, `failed` or
`cancelled`. Each `devices[].steps[]` entry has its own `status` (`pending`,
`running`, `completed`, `failed`) and a `message`. The JSON is compact
(`"status":"failed"`, no spaces) — parse it rather than grepping. The user sees the same
deployment live in the app. Delete `body.json` afterwards (it holds a password).

### 2.5 Verify

`completed` is not enough. Check the result is actually usable:

- Docker steps: on the target (`docker ps` locally, or over SSH) the
  solution's containers are `Up` and, if they define a health check, `(healthy)`.
- Services with a port: `curl -s -o /dev/null -w "%{http_code}" http://<host>:<port>/`
  returns 2xx/3xx.
- Tell the user the URL to open and anything the guide says to do next.

### 2.6 If anything failed

Go straight to §3 below with the `deployment_id`. Do not stop to ask.

To retry after a fix, send the same body again — same `preset_id` and
`device_connections` — with `selected_devices` listing only the device(s) that
failed; the others are already done. Leaving manual steps in is harmless (they
are skipped).

## 3. Diagnose through the app

The general method (classify, retry, report, issue form) is in `diagnose.md`; these are the app-specific evidence sources.

### 3.1 Find the deployment

If you started it, you already have the `deployment_id`. Otherwise:

```
curl -s "BASE/api/deployments"           # newest first: id, solution_id, status
curl -s "BASE/api/ai/context"            # what is running right now, and what the user is looking at in the app
```

### 3.2 Collect evidence

`/summary` and `/logs` only know deployments made since the app last started;
an older id from the list returns 404. In that case read the engine log (below)
for that time, or reproduce the failure by deploying again.

Start with the summary. **The real error is usually in the failing step's
`message`** (`devices[].steps[]` with `status: failed`); the top-level `errors`
list and the error-level logs may only say "Device X deployment failed".

```
curl -s "BASE/api/deployments/<deployment_id>/summary"
```

For more context around the failure, the full device log:

```
curl -s "BASE/api/deployments/<deployment_id>/logs?device_id=<device_id>&limit=300"
```

If the deployment logs are empty or end abruptly, read the engine log:
`<logs_dir>/provisioning-station.log` (last ~200 lines) and, if present,
`<logs_dir>/provisioning-station-crash.log`. `logs_dir` is in `runtime.json`.

Note the failing device, step and the first error — later errors are usually
consequences of the first.

### 3.3 Device checks, classification, retry, report

As in `diagnose.md` §3–6, with these differences: the solution folder is
`<solutions_dir>/<id>/` from `runtime.json`, or the edit copy if one exists;
configuration fixes go through §4; the issue form's `app_version` is
`app_version` from `runtime.json`, and its `diff` field is the output of
`/api/editor/solutions/<id>/diff`.

## 4. Change a solution's configuration

Needs `contract_version` 6 or later (see §1).

The app never changes its bundled solutions. Edits go into an **edit copy** of
one solution; while the edit copy exists, the app uses it instead of the
bundled one. Deleting it ("discard") restores the original. The app marks
the solution as "locally modified", shows the changes, and offers "restore
official version" — so the user can always see and undo what you changed.

### 4.1 Open the edit copy

```
curl -s -X POST "BASE/api/editor/solutions/<id>/enter"
```

Returns `path` — the edit copy's folder. Calling it again is safe; it keeps
existing edits and returns the same `path`.

### 4.2 Edit files in `path`

| File | Holds |
|---|---|
| `solution.yaml` | Name, presets, intro metadata |
| `guide.md`, `guide_zh.md` | Deployment steps; each `## Step` header has `config=devices/<x>.yaml` |
| `devices/<x>.yaml` | One step's settings: `docker.compose_file`, `docker.environment`, `docker.services[].port` / `health_check_endpoint`, `pre_checks`, `ssh.default_user`, firmware source, ... |
| `assets/...` | What gets deployed: compose files, Node-RED flows, scripts, firmware |

Field definitions:
https://raw.githubusercontent.com/suharvest/sensecraft-solutions/main/spec/device.schema.json
and `.../spec/solution.schema.json`.

Keep changes minimal: change what the evidence points at, nothing else. When a
value appears in several places (a port in compose, in `services[].port` and in
`pre_checks`), change all of them.

**Device YAMLs and assets are read from disk at deploy time**, so they take
effect as soon as you save them. Always validate before redeploying.

### 4.3 Validate

```
curl -s -X POST "BASE/api/editor/solutions/<id>/validate"
```

`ok: false` → fix each entry in `errors` (`file` is relative to `path`, `line`
is 1-based or null) and validate again. `warnings` do not block; leave
existing ones (e.g. "missing Chinese translation") alone unless the user asked
for guide changes.

### 4.4 Apply

```
curl -s -X POST "BASE/api/editor/solutions/<id>/apply"
```

- `200` with `active_path` equal to `path` → the edit copy is live, including
  changes to `solution.yaml` and the guides.
- `422` → `{"detail": <the same report as validate>}`; nothing was reloaded.
  Fix the `detail.errors` entries and retry.

Then redeploy the affected device (§2.6, or `deploy.md` §6 on the engine path).

### 4.5 Show what changed

```
curl -s "BASE/api/editor/solutions/<id>/diff"
```

Returns `files[]` with `path`, `status` (`modified` / `added` / `removed`) and a
unified `diff` for text files. Show the user these diffs. The same changes are
visible in the app.

### 4.6 Undo, share

- Undo all edits: `curl -s -X POST "BASE/api/editor/solutions/<id>/discard"`
- Package the edit copy as a zip (returns `zip_path`) to send to the solution
  maintainers or turn into a pull request:
  `curl -s -X POST "BASE/api/editor/solutions/<id>/export"`
- An app content update does not overwrite the edit copy. If the user later
  wants the updated official version, discard the edit copy.

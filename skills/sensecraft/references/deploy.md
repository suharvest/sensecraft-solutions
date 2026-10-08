# Deploy a solution

`BASE` comes from Step 0 in `SKILL.md`. Examples use `lang=en`; use `lang=zh`
for a Chinese-speaking user.

## 1. Find the solution

```
curl -s "BASE/api/solutions?lang=en"
```

Match the user's wording against `name` / `summary`. Confirm the `id` with the
user if more than one fits.

## 2. Read what the deployment needs

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

## 3. Fill in and confirm

Ask the user for every `<REQUIRED: ...>` value (device IP, username, password,
and any user inputs). For `docker_deploy` steps pick the target with
`"target": "<target id>"`; remote targets also need `host`, `username`,
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

## 4. Start and wait

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

## 5. Verify

`completed` is not enough. Check the result is actually usable:

- Docker steps: on the target (`docker ps` locally, or over SSH) the
  solution's containers are `Up` and, if they define a health check, `(healthy)`.
- Services with a port: `curl -s -o /dev/null -w "%{http_code}" http://<host>:<port>/`
  returns 2xx/3xx.
- Tell the user the URL to open and anything the guide says to do next.

## 6. If anything failed

Go straight to `diagnose.md` with the `deployment_id`. Do not stop to ask.

To retry after a fix, send the same body again — same `preset_id` and
`device_connections` — with `selected_devices` listing only the device(s) that
failed; the others are already done. Leaving manual steps in is harmless (they
are skipped).

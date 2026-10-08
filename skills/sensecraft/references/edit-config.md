# Change a solution's configuration

Needs `contract_version` 6 or later (see `SKILL.md` Step 0).

The app never changes its bundled solutions. Edits go into an **edit copy** of
one solution; while the edit copy exists, the app uses it instead of the
bundled one. Deleting it ("discard") restores the original. The app marks
the solution as "locally modified", shows the changes, and offers "restore
official version" — so the user can always see and undo what you changed.

## 1. Open the edit copy

```
curl -s -X POST "BASE/api/editor/solutions/<id>/enter"
```

Returns `path` — the edit copy's folder. Calling it again is safe; it keeps
existing edits and returns the same `path`.

## 2. Edit files in `path`

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

## 3. Validate

```
curl -s -X POST "BASE/api/editor/solutions/<id>/validate"
```

`ok: false` → fix each entry in `errors` (`file` is relative to `path`, `line`
is 1-based or null) and validate again. `warnings` do not block; leave
existing ones (e.g. "missing Chinese translation") alone unless the user asked
for guide changes.

## 4. Apply

```
curl -s -X POST "BASE/api/editor/solutions/<id>/apply"
```

- `200` with `active_path` equal to `path` → the edit copy is live, including
  changes to `solution.yaml` and the guides.
- `422` → the same report as `validate`; nothing was reloaded. Fix and retry.

Then redeploy the affected device (`deploy.md` §6).

## 5. Show what changed

```
curl -s "BASE/api/editor/solutions/<id>/diff"
```

Returns `files[]` with `path`, `status` (`modified` / `added` / `removed`) and a
unified `diff` for text files. Show the user these diffs. The same changes are
visible in the app.

## Undo, share

- Undo all edits: `curl -s -X POST "BASE/api/editor/solutions/<id>/discard"`
- Package the edit copy as a zip (returns `zip_path`) to send to the solution
  maintainers or turn into a pull request:
  `curl -s -X POST "BASE/api/editor/solutions/<id>/export"`
- An app content update does not overwrite the edit copy. If the user later
  wants the updated official version, discard the edit copy.

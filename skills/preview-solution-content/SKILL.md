---
name: preview-solution-content
description: PREVIEW locally edited solution content inside the user's installed SenseCraft Solution desktop app, without rebuilding the app. This is **preview only — not a release**. Use when the user says "本地预览一下", "我改了文案，App 里能看到吗", "把这个方案导进 App 看看效果", or similar. The real release path is OTA (`scripts/generate_solution_manifest.py` + commit `bundled_hashes.json`) and is a separate, intentional action — if the user wants to ship to all users, do NOT use this skill.
user_invocable: true
arguments:
  - name: solution_id
    description: "Solution ID to export and preview (optional — will list available ids if omitted)"
    required: false
---

# Preview Solution Content (Local-Only, NOT a Release)

Bridge "I edited files in the repo" → "I see it in my installed app, on my machine, right now". For non-technical users who can't / won't rebuild the desktop app.

## Preview vs. Release — read first

This skill is **preview only**. Concretely:

| Aspect | Preview (this skill) | Release (NOT this skill) |
|---|---|---|
| Where the content lands | Only the installed app on this machine | OSS CDN → all users via OTA |
| Touches Git? | No | Yes — commit `bundled_hashes.json` |
| Runs `generate_solution_manifest.py`? | No | Yes |
| Updates `manifest.json` / `bundled_hashes.json`? | No | Yes |
| Reversible? | Yes — reimport or restart app | Requires a follow-up release |
| Audience | Only the editor, for their own eyes | Everyone running the app |

If the user is asking to **ship** the change, **stop**. Tell them this is preview only and point at the release flow (`scripts/generate_solution_manifest.py` + `git commit bundled_hashes.json`). Get explicit confirmation before running anything that writes to a network or to git.

## When to use

- User edited Markdown / YAML / images under `solutions/<id>/` in the source tree
- They want to **see** how those edits render inside the already-installed desktop app
- They are explicitly previewing — no OTA, no commit, no `bundled_hashes.json` regen

## Workflow

### Step 1 — Ask user for the backend port

The desktop app uses a dynamic port. The user can read it from the app:

> 请在 App 内打开 **设置 → API 访问**，把"接口地址"里的端口号告诉我（例如 `http://127.0.0.1:3260` 里的 `3260`）。

Default is `3260` but Tauri may have picked another free port — always ask, don't assume.

> 注意：这里**不需要**勾选"启用局域网 API 访问"那个开关。那个开关只控制别的机器能不能访问；我们在同一台机器上跑命令，"接口地址"会一直显示，**本机请求免认证**。

Set `PORT=<user-provided>` and `BASE=http://127.0.0.1:$PORT` for the rest of the flow.

Sanity check the port is alive before doing anything else:

```bash
curl -fsS "$BASE/api/health" >/dev/null && echo "backend reachable" || echo "backend NOT reachable"
```

If unreachable, stop and ask the user to confirm the app is running.

### Step 2 — Confirm which solution to preview

If the user didn't specify a `solution_id`:

```bash
uv run python scripts/export_solution.py --list
```

Show the list, ask the user to pick.

### Step 3 — Export the zip

```bash
uv run python scripts/export_solution.py <solution_id>
# → produces dist/<solution_id>.zip
ZIP="$(pwd)/dist/<solution_id>.zip"
```

The zip format matches the app's import API (`solution.yaml` at root, other files relative). No further packing needed.

### Step 4 — Parse (dry-run validation)

```bash
PARSE=$(curl -fsS -X POST "$BASE/api/solutions/import/parse" -F "file=@$ZIP")
echo "$PARSE" | jq '{solution_id, name, conflict, files: (.files|length)}'
TEMP_ID=$(echo "$PARSE" | jq -r .temp_id)
SID=$(echo "$PARSE" | jq -r .solution_id)
CONFLICT=$(echo "$PARSE" | jq -r .conflict)
```

Show the user the parsed summary (id, name, file count, whether it conflicts with an existing solution).

### Step 5 — Apply (overwrite by default)

For this skill's purpose (preview an edit of an existing solution), `conflict_resolution=overwrite` is the right default — the user is editing their own solution, not importing a new one.

```bash
curl -fsS -X POST "$BASE/api/solutions/import/apply" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg t "$TEMP_ID" --arg i "$SID" \
      '{temp_id:$t, id:$i, conflict_resolution:"overwrite"}')" \
  | jq '{id, name, category, solution_type}'
```

If `CONFLICT=false` (brand new solution being imported), still pass `overwrite` — it's a no-op for the non-conflict case.

### Step 6 — Verify in the app

Ask the user to:

1. Refresh the solution list page in the app (or restart the app if cached aggressively)
2. Open the solution detail page and confirm their edits are visible

If they see the new content → done. No further action.

## Constraints

- **Don't touch git.** This skill never runs `git add`, `git commit`, or modifies `bundled_hashes.json`. The user's repo state is unchanged.
- **Don't regenerate the OTA manifest.** That's a separate, intentional publish flow.
- **Don't auto-discover the port.** Always ask the user — the app exposes it in Settings → API 访问, and asking avoids hitting the wrong instance (e.g., a parallel dev server).
- **Local-only auth assumption.** Requests to `127.0.0.1` on this app don't need an API key. If the user is hitting it across LAN, they'd need an `X-API-Key` header — but that's out of scope here.
- **Single solution at a time.** If the user edited multiple solutions, loop the workflow per id; don't batch silently.

## Failure modes & quick fixes

| Symptom | Cause | Fix |
|---|---|---|
| `curl: (7) Failed to connect` on health check | Wrong port, or app not running | Ask user to recheck Settings → API 访问 |
| `parse` returns 400 "missing solution.yaml" | Zip built from wrong dir | Verify `solutions/<id>/solution.yaml` exists in source |
| `apply` returns conflict error despite overwrite | Editor overlay (`solutions_edits/<id>/`) is shadowing the import | Ask user to clear edits via the app's editor UI, or accept that preview will reflect overlay, not import |
| User sees old content after import | Frontend caches the solution list | Hard refresh / restart app |

## What this skill does NOT do

- Does not modify `solutions_edits/` or `solutions_updates/` directly — the import API decides where to land the content.
- Does not publish to OSS or update bundled hashes.
- Does not run any device-side deploy. For deploy, route to `/deploy-solution`.

---
name: solution-app-preview
description: Preview local solution edits in the SenseCraft Solution engine app (app_collaboration), and bind the app's solutions submodule for publish. Use when the user wants to "本地预览方案", "在 app 里看方案改动", run the dev app against this working solutions repo, or update/bind the app's sensecraft-solutions submodule.
---
# Solution App Preview

Bridge this **working repo** and the **engine app** `app_collaboration`, which mounts solutions as a git **submodule** at `app_collaboration/sensecraft-solutions/`.

Two independent scenarios, kept decoupled:

| Scenario | Command | What it does |
|---|---|---|
| **Local dev (fast)** | `preview.sh preview` | Runs the app's `dev.sh` with `PS_SOLUTIONS_DIR=<this-repo>/solutions`. App reads this repo directly — **uncommitted edits show on refresh**. Submodule untouched. |
| **Publish** | `preview.sh bind [ref]` | Moves the app submodule pointer to this repo's HEAD (fetched locally). Warns if that commit isn't on `origin` yet. |

**Why this works:** the app resolves its solutions directory from `PS_SOLUTIONS_DIR` (authoritative, `provisioning_station/config.py`), falling back to the submodule. So the fast path is a pure runtime override that never dirties the submodule or the pin. The submodule pin stays the release source-of-truth, bumped only at publish time.

## User-invocable
Trigger: /solution-app-preview
Script: `skills/solution-app-preview/preview.sh` (paths auto-derive from the script location; override the app repo with `PS_APP` if your layout differs)

## Commands

```bash
SKILL=skills/solution-app-preview/preview.sh   # from the repo root

# Fastest local preview — dev app reads this repo live (no sync).
# Long-running; run it in your own terminal, or background it.
"$SKILL" preview

# Just the env line, to fold into your own launch flow:
"$SKILL" env        # -> export PS_SOLUTIONS_DIR=.../sensecraft-solutions/solutions

# Publish: bind the app submodule to this repo's HEAD (or a ref).
"$SKILL" bind
"$SKILL" bind 6b483a2

# Revert the submodule to the commit the app repo pins.
"$SKILL" restore

# Show working-repo HEAD vs app submodule pin.
"$SKILL" status
```

## Notes / gotchas
- **`preview` is the day-to-day path.** It starts the dev server (foreground). When invoking on the user's behalf, run it with `run_in_background: true` (or just print the command) — don't block.
- **`bind` for publish requires a pushed commit.** The app submodule pin references a SHA that must exist on the solutions `origin`. `bind` warns when HEAD isn't pushed; push solutions first, then commit the app submodule bump.
- **Reload behavior:** the backend serves solutions from `solutions_dir`; after editing, refresh the solution list / re-open the deploy page. If a change isn't picked up (e.g. cached), restart the dev backend.
- **Paths:** SRC is derived from the script location (this repo). APP defaults to a sibling `../app_collaboration`; override with `PS_APP`.
- Do **not** use this to ship to end users — OTA (`scripts/generate_solution_manifest.py` + `bundled_hashes.json`) is the real release path. This is preview + submodule wiring only.

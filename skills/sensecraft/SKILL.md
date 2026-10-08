---
name: sensecraft
description: Deploy, troubleshoot and adjust SenseCraft Solution IoT solutions through the SenseCraft Solution app running on this computer. Use when the user wants to deploy a SenseCraft / Seeed Studio solution to a device (Jetson, reComputer, reCamera, Raspberry Pi, SenseCAP Watcher, ...), when a deployment failed or a deployed solution does not work, or when a solution's configuration (ports, images, environment variables, device settings) needs to change.
---

# SenseCraft Solution

This skill drives the SenseCraft Solution desktop app through its local HTTP API.
It works in any agent that can read files and run shell commands: every command
is plain `curl`, available on macOS, Linux and Windows 10+.

> **Windows PowerShell:** `curl` there is an alias for `Invoke-WebRequest`.
> Always type `curl.exe`. Send JSON bodies from a file (`--data @body.json`)
> instead of inline strings to avoid quoting problems.

## Rules

1. **Credentials:** never invent a host, username or password — ask the user.
   Replace passwords with `<REDACTED>` in anything you show or log.
2. **What you may do without asking, and what needs the user's OK:**

   | Action | Ask first? |
   |---|---|
   | Read app status, deployment logs, engine log files | No |
   | Read-only checks on a device over SSH (`docker ps`, `docker logs`, `df -h`, `ss -ltnp`, `ping`) | No |
   | Edit the solution's edit copy (see `references/edit-config.md`) | No — show the diff afterwards; it can be reverted in one call |
   | Turn on the app's editor mode | **Yes** |
   | Change anything on a device: stop/remove containers, delete files, install packages, change system settings | **Yes** |
   | Redeploy | First retry: no. Every later retry: **yes** |
   | Open a GitHub issue or pull request | **Yes** |

3. **At most 3 fix-and-retry rounds** per problem. After that, stop and give the
   user a report (what failed, what you checked, what you changed).
4. Never edit files under `solutions_dir` (the app's bundled copy). Only edit the
   edit copy described in `references/edit-config.md`.

## Step 0 — Connect to the app (every task)

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

Below, `BASE` means the `base_url` value. Add `lang=zh` to API calls that take
`lang` when the user writes in Chinese, `lang=en` otherwise.

## Pick the task

| The user wants to... | Read |
|---|---|
| Deploy a solution | `references/deploy.md` |
| Find out why a deployment failed or a deployed solution misbehaves | `references/diagnose.md` |
| Change a solution's configuration | `references/edit-config.md` |

The three connect: **a failed deployment goes straight to `diagnose.md`**
without stopping to ask; a configuration fix goes through `edit-config.md`;
the retry goes back to `deploy.md` for the failed device only.

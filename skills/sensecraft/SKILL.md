---
name: sensecraft
description: Deploy and troubleshoot SenseCraft Solution IoT solutions with the `sensecraft-engine` command-line engine (no desktop app needed). Use when the user wants to deploy a SenseCraft / Seeed Studio solution to a device (Jetson, reComputer, reCamera, Raspberry Pi, SenseCAP Watcher, Grove Vision AI, ...), when a deployment failed or a deployed solution does not work, or when a deployment stops at a verification step that needs the user (people-counting lines, face enrollment, servo setup, robot arm check). Changing a solution's configuration needs the desktop app (references/app-only.md).
---

# SenseCraft Solution

This skill drives the `sensecraft-engine` command-line engine. It works in any
agent that can read files and run shell commands. Every step is a
`sensecraft-engine` command; the engine starts its own background instance when
a command needs one. Do not call the instance's HTTP port with `curl`: use the
CLI, and `sensecraft-engine api <METHOD> <path>` for anything without its own
command.

Capabilities that need the **SenseCraft Solution desktop app** (editing a
solution's configuration, the app's `/api/ai/context`, diagnosing through the
app's logs) are in `references/app-only.md`. Use them only when the user has
the app running.

## Rules

1. **Credentials:** never invent a host, username or password — ask the user.
   Replace passwords with `<REDACTED>` in anything you show or log.
2. **What you may do without asking, and what needs the user's OK:**

   | Action | Ask first? |
   |---|---|
   | Read deployment status and logs (`status`, `logs`), engine log files, `doctor`, `device list/ports/scan` | No |
   | Read-only checks on a device over SSH (`docker ps`, `docker logs`, `df -h`, `ss -ltnp`, `ping`) | No |
   | Edit the solution's edit copy (desktop app only, see `references/app-only.md`) | No — show the diff afterwards; the user sees it in the app as "locally modified" and can restore the official version in one click |
   | Anything a person does with their hands: plug in or swap a cable, connect a servo, sit in front of a camera, walk across a counting line, move or stand near a robot arm | **Yes** — tell the user what to do and wait for them to confirm it is done |
   | Commands that move hardware (`robot torque`, `robot actions test`) | **Yes** — the user confirms nobody is within reach first |
   | Change anything on a device: stop/remove containers, delete files, install packages, change system settings; `--replace-existing` | **Yes** |
   | Redeploy | First retry: no. Every later retry: **yes** |
   | Cancel a running deployment | **Yes** — it can leave a device half-configured |
   | Prepare an issue report (the user submits it) or open a pull request | **Yes** |

3. **At most 3 fix-and-retry rounds** per problem. After that, stop and give the
   user a report (what failed, what you checked, what you changed).
4. Never edit files under the engine's content directory
   (`~/.sensecraft/content/`) or the app's bundled solutions. Configuration
   changes go through the desktop app's edit copy (`references/app-only.md`).

## Step 0 — Install the engine and the solutions (every task)

1. Check whether it is installed: `sensecraft-engine --version`. If the command
   is not found, also try `~/.sensecraft/bin/sensecraft-engine --version`
   (Windows: `%USERPROFILE%\.sensecraft\bin\sensecraft-engine.cmd`); the
   installer puts it there and prints the `PATH` line to add.
2. Not installed → install it together with the solutions (ask the user first,
   it downloads a program):

   ```
   curl -fsSL https://sensecraft-statics.seeed.cc/engine/install.sh | sh -s -- --with-content
   ```

   Windows PowerShell:

   ```
   & ([scriptblock]::Create((irm https://sensecraft-statics.seeed.cc/engine/install.ps1))) -WithContent
   ```

3. Solutions are downloaded separately from the engine:

   | Command | Does |
   |---|---|
   | `sensecraft-engine content status --json` | Compares local solutions with the online list (`--offline`: local only) |
   | `sensecraft-engine content pull` | Downloads every solution (first run), or only `--solution <id>` |
   | `sensecraft-engine content update` | Re-downloads installed solutions that changed online |

   A command that finds no solutions exits with code 3 and says to run
   `content pull`. After `content pull` / `update`, if an engine instance is
   already running it keeps the solutions it loaded at start: run
   `sensecraft-engine daemon stop` when no deployment is running.
4. Device pre-checks on this computer: `sensecraft-engine doctor --json`. Each
   check has `status` (`ok` / `warn` / `fail`) and a `fix` command. Show the
   user any `fail` and its `fix`; running a `fix` changes this computer and
   needs their OK.

Use `--lang zh` on commands that take `--lang` when the user writes in Chinese,
`--lang en` otherwise.

## Exit codes (all commands)

| Code | Meaning | Next step |
|---|---|---|
| 0 | Success / accepted | Continue |
| 1 | Deployment failed, cancelled or interrupted; for `counting` / `face` / `wizard` / `robot`: the device did not confirm | `references/diagnose.md` |
| 2 | Bad or missing parameters; stdout has `{"type":"error","code":"missing_params","missing":[...]}` | Ask the user for each `missing` field, run again |
| 3 | Environment or conflict: no solutions (`content pull`), device busy with another deployment (409), engine instance shutting down or incompatible, serial port busy | Read the message; wait or fix, then run again |
| 4 | This step needs the desktop app (deployer not in the engine) | Tell the user to deploy this solution from the SenseCraft Solution app |
| 5 | Internal engine error | Engine bug: `references/diagnose.md` §6 |

## Pick the task

| The user wants to... | Read |
|---|---|
| Deploy a solution | `references/deploy.md` |
| Finish a step that reported `verify_required` (dashboards, counting lines, face enrollment, servo setup, robot arm) | `references/verify.md` |
| Find out why a deployment failed or a deployed solution misbehaves | `references/diagnose.md` |
| Deploy on a site without internet (prepare an offline package first) | `references/offline.md` |
| Change a solution's configuration, or use the desktop app's API | `references/app-only.md` (requires the desktop app) |

They connect: **a failed deployment goes straight to `diagnose.md`** without
stopping to ask; a `verify_required` event goes to `verify.md`; the retry goes
back to `deploy.md` for the failed device only.

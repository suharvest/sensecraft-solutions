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

1. **Credentials and secrets:** never invent a host, username or password —
   ask the user. Replace passwords, tokens, API keys and any other secret a
   deployment prints (for example a gateway token) with `<REDACTED>` in
   anything you show or log. Tell the user where to find the value (on the
   device, in the solution's page, in the file that holds it) instead of
   printing it.
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

3. **At most 3 fix-and-retry rounds** per problem for deterministic failures
   (wrong parameter, missing file, port taken, bad credentials, a container
   that exits). After that, stop and give the user a report (what failed, what
   you checked, what you changed). Transient registry or network errors follow
   the backoff rule in `references/deploy.md` §6 and do not use up a round.
4. Never edit files under the engine's content directory
   (`~/.sensecraft/content/`) or a resource solution directory. The binary
   embeds the device catalog; solution files come from a pulled content
   directory or an explicitly supplied resource/solutions directory. Configuration
   changes go through the desktop app's edit copy (`references/app-only.md`).
5. **Reading output:** read the CLI's JSON output directly; it is small. If a
   filter is needed, use `jq` only when it is already installed. Do not start
   python, node or any other interpreter to parse output. Where a command has
   a flag that prints just what you need (`--json`, `--preset`, `--device`,
   `--since`), use it.
6. **Temp files:** keep request bodies and scratch files in the current
   working directory under `./.sensecraft-work/`, never in `/tmp`. Remove the
   directory when the task ends, also after a failure.

## Step 0 — Install the engine and the solutions (every task)

1. Check whether it is installed: `sensecraft-engine --version`. If the command
   is not found, also try `~/.sensecraft/bin/sensecraft-engine --version`
   (Windows: `%USERPROFILE%\.sensecraft\bin\sensecraft-engine.cmd`); the
   installer puts it there and prints the `PATH` line to add.
2. Before running an installer, check its local prerequisites. On Unix run
   `command -v curl || command -v wget`, `command -v sha256sum || command -v shasum`,
   `command -v tar`, `command -v jq`, and `command -v minisign`. On Windows
   PowerShell run `Get-Command irm`, `Get-Command Invoke-WebRequest`,
   `Get-Command Expand-Archive`, `Get-Command ConvertFrom-Json`, and
   `Get-Command minisign`. Windows uses PowerShell/.NET ZIP and JSON support;
   it does not require `tar` or `jq`. If any check fails, report the missing
   command and stop; do not install packages or start another interpreter.
   `minisign` is required to verify the signed release manifest; Unix `jq` is
   required by the shell installer to read it.
3. Not installed → install it together with the solutions (ask the user first,
   it downloads a program):

   ```
   curl -fsSL https://sensecraft-statics.seeed.cc/engine/install.sh | sh -s -- --with-content
   ```

   If `curl` is unavailable but `wget` passed the prerequisite check, use the
   equivalent command:

   ```
   wget -qO- https://sensecraft-statics.seeed.cc/engine/install.sh | sh -s -- --with-content
   ```

   Windows PowerShell:

   ```
   & ([scriptblock]::Create((irm https://sensecraft-statics.seeed.cc/engine/install.ps1))) -WithContent
   ```

4. Solutions are downloaded separately from the engine:

   | Command | Does |
   |---|---|
   | `sensecraft-engine content status --offline --json` | Reads the local content store only; an empty store is a normal result with `installed: 0` and exit code 0 |
   | `sensecraft-engine content status --json` | Compares local solutions with the online list |
   | `sensecraft-engine content pull` | Downloads every solution (first run), or only `--solution <id>` |
   | `sensecraft-engine content update` | Re-downloads installed solutions that changed online |

   Run the offline status check before deciding whether content is installed.
   If it returns exit code 0 with `installed: 0`, run `content pull`; do not
   treat that status result as an error. A solution query such as `solution
   list` or `deploy-info` exits with code 3 when no usable resource/solution
   directory is available and tells you to run `content pull`. If a usable
   directory exists but the requested solution ID is unknown, the query exits
   with code 2. After `content pull` / `update`, if an engine instance is
   already running it keeps the solutions it loaded at start: run
   `sensecraft-engine daemon stop` when no deployment is running.
5. Device pre-checks on this computer: `sensecraft-engine doctor --json`. Each
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
| 2 | Invalid arguments or request. A `missing_params` error includes `missing[]`; an unknown ID or malformed JSON is also code 2 and may have no `missing[]` | Ask for each field only when `missing[]` is present; otherwise inspect the ID, JSON shape and parameter spelling, then correct or ask for the specific value |
| 3 | Environment or conflict: a solution query has no usable resource/solution directory (`content pull`), device busy with another deployment (409), engine instance shutting down or incompatible, serial port busy | Read the message; pull content or fix the environment, then run again. An empty `content status --offline` store is exit 0, not this case |
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

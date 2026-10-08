# Diagnose a failed or misbehaving deployment

Follow the rules in `SKILL.md` (what needs the user's OK, at most 3 rounds).

## 1. Find the deployment

If you started it, you already have the `deployment_id`. Otherwise:

```
curl -s "BASE/api/deployments"           # newest first: id, solution_id, status
curl -s "BASE/api/ai/context"            # what is running right now, and what the user is looking at in the app
```

## 2. Collect evidence

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

## 3. Check the device (read-only, no need to ask)

Which containers belong to the solution: in the solution folder
(`<solutions_dir>/<id>/`, or the edit copy if one exists) the step's
`devices/<x>.yaml` names the compose file (`docker.compose_file`) and project
(`docker.options.project_name`); the compose file may set `container_name`.
`docker ps -a --filter label=com.docker.compose.project=<project_name>` lists
them.

For remote targets, SSH with the credentials the user gave for the deployment:

```
docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker logs --tail 100 <container>
df -h /
ss -ltnp            # who holds a port (use: sudo ss -ltnp if names are hidden)
ping -c 2 8.8.8.8   # internet reachability
```

For local targets run the same commands on this computer (Windows: Docker
Desktop must be running; use `docker` the same way).

## 4. Classify, then act

Match the evidence against `error-catalog.md`. Every problem falls in one of
three classes:

| Class | Example | What you do |
|---|---|---|
| **Device / environment** | port taken, disk full, Docker missing, network blocked, wrong password | Propose the exact fix commands → user OK → run them → retry |
| **Solution configuration** | wrong port in compose, health check hits an auth endpoint, missing env var, bad image tag | Fix it in the edit copy (`edit-config.md`) → validate → apply → retry |
| **Engine bug** | traceback inside `provisioning_station`, a step that fails the same way on any device, behaviour contradicting the solution's own config | Stop. Write the issue draft below |

If the evidence does not fit any row, say so and show the user the first error
with your best hypothesis and what would confirm it. Do not guess-and-retry.

## 5. Retry

Restart only the failed device (`selected_devices` = that device, see
`deploy.md` §6). First retry without asking; later ones need the user's OK.
After 3 rounds without success, stop and report.

## 6. Report

Always finish with: what failed, the evidence (first error line), what you
changed (commands run, files edited with a diff), and the result.

### Engine bug: issue draft

Give the user this draft and ask before submitting it to
https://github.com/suharvest/sensecraft-solutions/issues :

```
Title: [engine] <step type> fails: <first error, one line>

App version: <app_version from runtime.json>  Contract: <contract_version>
OS: <this computer's OS>   Target device: <model / OS / arch>
Solution: <solution_id>  Preset: <preset_id>  Step: <step id> (<type>)
Edited locally: yes/no (attach the diff if yes)

What happened:
<first error and the 10–20 log lines around it, passwords and IPs redacted>

Reproduce:
1. ...
What was ruled out: <device checks that passed>
```

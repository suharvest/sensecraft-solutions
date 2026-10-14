# Error catalog

Match the **first** error of the failing step. Class: **Env** = device /
environment, **Config** = solution configuration, **Engine** = engine / app bug.

| Evidence | Class | Cause | Action |
|---|---|---|---|
| Exit 3, "no solutions" / hint to run `content pull` | Env | Solutions not downloaded yet | `sensecraft-engine content pull`, then run the command again |
| Exit 2, `{"type":"error","code":"missing_params","missing":[...]}` | Env | A required value is not in the request | Ask the user for each `missing` field (`preset_id`, `device_connections.<id>.<key>`) |
| Exit 3, HTTP 409 with `busy: [...]` | Env | Another deployment is using the same device | Wait for it (`status <id>`), or ask the user whether to cancel it |
| Exit 4, `requires_desktop_app` | Env | This step's deployer is not in the engine | Tell the user to deploy the solution from the SenseCraft Solution app |
| `key_file` refused (outside `~/.ssh`) | Env | The engine only reads SSH keys inside `~/.ssh` or its data directory | Use a key under `~/.ssh` (copying a key there needs the user's OK) |
| `the offline package was prepared with different values: ...` | Env | Deploy parameters differ from the ones the offline package was prepared with | Plan / prepare again with the deploy's values (`offline.md`), or deploy with the prepared values |
| `doctor` serial check: not a member of `dialout`; serial port permission denied | Env | User may not open USB serial ports (Linux) | Propose the `fix` from `doctor` (`sudo usermod -aG dialout <user>`, then log out and in) — user OK |
| `port_busy` from `counting` / `face` / `wizard` | Env | A deployment or another session holds the serial port | Wait until it finishes; do not force it |
| `Missing host` / connection fields empty | Env | `host` not given in `device_connections` | Ask the user for the device IP, redeploy |
| SSH `Authentication failed` / `Permission denied (publickey,password)` | Env | Wrong username or password | Ask the user to re-check; the solution's default user is in `request_template` |
| SSH timeout / `No route to host` | Env | Device off, wrong IP, other network | `ping` it; ask the user to check power and that both are on the same LAN |
| `port is already allocated` / `address already in use`; pre-check `port_available` failed | Env | Another process or container holds the port | `ss -ltnp` / `docker ps` to find it; propose stopping it (user OK), or change the port in config |
| `Conflict. The container name ... is already in use` | Env | Leftover container from an earlier deployment | Redeploy with `"auto_replace_containers": true` after the user agrees |
| `no space left on device`; pre-check `disk_space` failed | Env | Disk full | `df -h`, `docker system df`; propose `docker image prune` (user OK) |
| `docker: command not found`; pre-check `docker_version` failed | Env | Docker not installed / too old | Tell the user; installing needs their OK |
| `permission denied while trying to connect to the Docker daemon socket` | Env | User not in `docker` group | Propose `sudo usermod -aG docker <user>` then re-login (user OK) |
| Image pull: `TLS handshake timeout`, `i/o timeout`, `toomanyrequests` | Env | Registry unreachable or rate-limited | Look for `Mirror context resolved` in the logs: absent → mirror detection failed; retry once, then report network status to the user |
| `manifest unknown` / `not found` for an image | Config | Image name or tag wrong, or not built for the device's CPU (arm64 vs amd64) | `docker manifest inspect <image>` (read-only): "no such manifest" → the tag does not exist, fix it; it exists but lists no platform matching the device's `uname -m` → wrong architecture, pick an image built for it |
| Container `Restarting` / `Exited (1)`; error in `docker logs` | Config (usually) | App inside the container misconfigured: env var, mounted path, port | Read `docker logs`; fix the compose / env in the edit copy (`app-only.md` §4), or report it |
| Container `(healthy)` but the step reports health-check failure | Config | `health_check_endpoint` points at a URL that returns 401/404 | Fix the endpoint in the device YAML (`docker.services[].health_check_endpoint`) |
| Containers up, but the page / port does not answer from another machine | Env | Device firewall | Check `sudo iptables -L -n` / `ufw status`; propose opening the port (user OK) |
| USB device not detected (`No device found`, `detect` returns nothing) | Env | Cable is charge-only, wrong port, driver missing | Ask the user to replug with a data cable; on Windows check Device Manager for a COM port |
| YAML / validation error naming a solution file | Config | Broken solution file | Desktop app: fix it in the edit copy (`app-only.md` §4); `validate` gives file and line. Engine only: run `sensecraft-engine content update`; still failing → report it |
| Python traceback mentioning `provisioning_station/` | Engine | App bug | Issue report (`diagnose.md` §6) |
| `sensecraft-engine` exits 5, or a panic in `~/.sensecraft/logs/engine.log` | Engine | Engine bug | Issue report (`diagnose.md` §6) |
| Same step fails identically on two different devices after the environment checks pass | Engine (likely) | App bug | Issue report (`diagnose.md` §6) |

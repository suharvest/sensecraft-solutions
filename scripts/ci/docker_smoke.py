#!/usr/bin/env python3
"""Engine-free docker-compose smoke harness for SenseCraft solutions.

Tier-3 deploy validation, public-CI flavour: this only proves that an
``opt-in`` ``docker_deploy`` preset's compose stack **comes up** and that each
declared service's health endpoint responds (HTTP < 500). It does NOT validate
that the produced data / inference results are correct — that is out of scope
for a smoke test and generally not verifiable in CI.

Contract (read straight from the solution's ``devices/*.yaml``)::

    type: docker_deploy
    docker:
      ci_smoke: true                      # <-- opt-in marker (REQUIRED to run)
      compose_file: ../docker/docker-compose.yml   # relative to device YAML dir
      environment: { KEY: value, ... }
      options: { project_name: my-project }
      services:
        - { name: influxdb, port: 8086, health_check_endpoint: /health, required: true }

Presets without ``docker.ci_smoke: true`` are skipped (heavy / GPU / hardware
solutions deliberately do not smoke on x86 CI).

Hard rules:
  * stdlib + PyYAML only. NO import of provisioning_station /
    sensecraft_solution_spec — this runs in the public repo CI.
  * env is injected via a temporary ``--env-file`` — the original compose file
    is never modified.
  * teardown ALWAYS runs (try/finally) and is project-scoped:
    ``docker compose -p <project> down -v``. Never a bare ``docker compose down``.

Exit code: 0 = all smoked presets PASS, 1 = any FAIL / nothing eligible erred.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency hint
    print("ERROR: PyYAML is required (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)


HEALTH_TIMEOUT_S = 120      # per-service polling budget
POLL_INTERVAL_S = 3
COMPOSE_UP_TIMEOUT_S = 600
COMPOSE_DOWN_TIMEOUT_S = 180


def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list[str], timeout: int, **kwargs) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, timeout=timeout, text=True, **kwargs)


def find_docker_deploy_presets(solution_dir: Path, preset: str | None) -> list[tuple[Path, dict]]:
    """Return [(device_yaml_path, parsed_dict), ...] for opt-in docker_deploy presets."""
    devices_dir = solution_dir / "devices"
    if not devices_dir.is_dir():
        log(f"No devices/ dir in {solution_dir}")
        return []

    found: list[tuple[Path, dict]] = []
    for yml in sorted(devices_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(yml.read_text())
        except Exception as exc:  # noqa: BLE001
            log(f"  skip {yml.name}: parse error: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        if data.get("type") != "docker_deploy":
            continue
        if preset and data.get("id") != preset:
            continue
        docker = data.get("docker") or {}
        if not docker.get("ci_smoke"):
            log(f"  skip {yml.name}: no docker.ci_smoke marker (not eligible for CI smoke)")
            continue
        found.append((yml, data))
    return found


def resolve_compose_file(device_yaml: Path, compose_rel: str) -> Path:
    """Resolve docker.compose_file the way the engine does: relative to the
    **solution root**, not to the device YAML's own directory.

    The engine sets ``base_path`` to the solution directory
    (solution_manager.py:1082) and resolves assets with
    ``resolve_within(base_path, relative_path)`` (:1184), which also rejects
    paths escaping the solution root. Resolving against ``devices/`` here
    instead made this script accept exactly the paths the engine rejects
    (``../docker/x.yml`` resolves fine from ``devices/`` but escapes the root)
    and reject the ones it accepts (``assets/docker/x.yml``) — i.e. the smoke
    test was green precisely when the real deployment was broken.
    """
    solution_root = device_yaml.parent.parent
    return (solution_root / compose_rel).resolve()


def write_env_file(environment: dict) -> Path | None:
    """Write declared environment to a temp --env-file. Original compose untouched."""
    if not environment:
        return None
    fd, path = tempfile.mkstemp(prefix="smoke-env-", suffix=".env")
    with os.fdopen(fd, "w") as fh:
        for key, value in environment.items():
            fh.write(f"{key}={value}\n")
    return Path(path)


def poll_health(name: str, port: int, endpoint: str) -> bool:
    """Poll http://127.0.0.1:<port><endpoint> until HTTP < 500 or timeout."""
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    url = f"http://127.0.0.1:{port}{endpoint}"
    deadline = time.time() + HEALTH_TIMEOUT_S
    attempt = 0
    last_err = ""
    while time.time() < deadline:
        attempt += 1
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = resp.getcode()
                if code < 500:
                    log(f"  [{name}] HTTP {code} from {url} (attempt {attempt}) -> UP")
                    return True
                last_err = f"HTTP {code}"
        except urllib.error.HTTPError as exc:
            # An HTTP response (even 4xx) means the service is listening.
            if exc.code < 500:
                log(f"  [{name}] HTTP {exc.code} from {url} (attempt {attempt}) -> UP")
                return True
            last_err = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - connection refused, etc.
            last_err = type(exc).__name__
        time.sleep(POLL_INTERVAL_S)
    log(f"  [{name}] {url} never healthy within {HEALTH_TIMEOUT_S}s (last: {last_err}) -> DOWN")
    return False


def smoke_preset(device_yaml: Path, data: dict) -> bool:
    docker = data["docker"]
    project = (docker.get("options") or {}).get("project_name")
    if not project:
        log(f"FAIL {device_yaml.name}: docker.options.project_name is required for project-scoped teardown")
        return False

    compose_file = resolve_compose_file(device_yaml, docker["compose_file"])
    if not compose_file.is_file():
        log(f"FAIL {device_yaml.name}: compose file not found: {compose_file}")
        return False

    services = docker.get("services") or []
    env_file = write_env_file(docker.get("environment") or {})

    base = ["docker", "compose", "-p", project, "-f", str(compose_file)]
    if env_file:
        base += ["--env-file", str(env_file)]

    log("")
    log(f"=== SMOKE preset '{data.get('id')}' (project={project}) ===")
    log(f"    compose: {compose_file}")
    log(f"    services: {[s.get('name') for s in services]}")

    overall_ok = True
    try:
        up = run(base + ["up", "-d", "--remove-orphans"], timeout=COMPOSE_UP_TIMEOUT_S,
                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log(up.stdout or "")
        if up.returncode != 0:
            log(f"FAIL: `compose up` exited {up.returncode}")
            return False

        for svc in services:
            name = svc.get("name")
            port = svc.get("port")
            endpoint = svc.get("health_check_endpoint", "/")
            required = svc.get("required", True)
            if port is None:
                log(f"  [{name}] no port declared -> skip health poll")
                continue
            ok = poll_health(name, port, endpoint)
            if not ok and required:
                log(f"  [{name}] REQUIRED service unhealthy -> preset FAIL")
                overall_ok = False
            elif not ok:
                log(f"  [{name}] optional service unhealthy (tolerated)")
    finally:
        # teardown ALWAYS, project-scoped, with -v to drop volumes. Never bare down.
        log("")
        log(f"--- teardown: docker compose -p {project} down -v ---")
        try:
            down = run(["docker", "compose", "-p", project, "-f", str(compose_file)] +
                       (["--env-file", str(env_file)] if env_file else []) +
                       ["down", "-v", "--remove-orphans"],
                       timeout=COMPOSE_DOWN_TIMEOUT_S,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log(down.stdout or "")
        except Exception as exc:  # noqa: BLE001
            log(f"WARNING: teardown raised {exc}")
        if env_file:
            try:
                env_file.unlink()
            except OSError:
                pass

    log(f"=== preset '{data.get('id')}': {'PASS' if overall_ok else 'FAIL'} ===")
    return overall_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Engine-free docker-compose smoke harness")
    parser.add_argument("solution_dir", help="Path to a solution directory")
    parser.add_argument("--preset", help="Only smoke the device YAML with this id", default=None)
    args = parser.parse_args()

    solution_dir = Path(args.solution_dir).resolve()
    if not solution_dir.is_dir():
        log(f"ERROR: not a directory: {solution_dir}")
        return 2

    presets = find_docker_deploy_presets(solution_dir, args.preset)
    if not presets:
        log(f"No eligible docker_deploy presets (with docker.ci_smoke: true) in {solution_dir}")
        # Nothing to smoke is not a failure of the harness, but signal clearly.
        return 0

    results: dict[str, bool] = {}
    for device_yaml, data in presets:
        results[device_yaml.name] = smoke_preset(device_yaml, data)

    log("")
    log("==================== SUMMARY ====================")
    for name, ok in results.items():
        log(f"  {name}: {'PASS' if ok else 'FAIL'}")
    all_ok = all(results.values())
    log(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fail when a declared compose file would be skipped by the mirror rewrite.

The engine only rewrites images to a CN mirror for files whose *name* it
recognises as a compose file (``docker_remote_deployer._looks_like_compose_file``).
A file the matcher rejects is uploaded verbatim, so public images such as
``mysql:latest`` get pulled straight from Docker Hub — which times out on a
restricted network. The deploy log only says "Pull failed" and points nowhere
near the filename, so catch it here instead.

Files are discovered from what device YAMLs actually declare (``compose_file``
/ ``compose_dir``), not by guessing from filenames: a guard that pre-filters on
the same prefix it is testing would be blind to exactly the names that break
(e.g. ``cv-docker-compose.yml``).

Keep ``looks_like_compose_file`` in sync with the engine's implementation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS = ROOT / "solutions"

# Mirror of provisioning_station.deployers.docker_remote_deployer
# ._looks_like_compose_file — keep the two in sync.
def looks_like_compose_file(name: str) -> bool:
    lower = name.lower()
    if not (lower.endswith(".yml") or lower.endswith(".yaml")):
        return False
    stem = lower.rsplit(".", 1)[0]
    root = stem.split(".", 1)[0]
    if root in ("docker-compose", "compose"):
        return True
    return root.startswith("docker-compose-") and len(root) > len("docker-compose-")


_COMPOSE_FILE = re.compile(r"^\s*compose_file:\s*(\S+)", re.MULTILINE)

# Names the engine does not recognise, kept because renaming them would mean
# touching every device YAML that references them. Safe *only* while every
# image inside is on a private registry (first path segment contains "." or
# ":"), which the engine skips anyway — so the rewrite being skipped costs
# nothing. Add a public image to one of these and it will silently pull from
# Docker Hub on a restricted network: rename the file instead of extending
# this list.
_GRANDFATHERED: dict[str, str] = {
    "cv-docker-compose.yml": "ai_lab — ghcr.io images only",
    "cv-docker-compose-rk3588.yml": "ai_lab — ghcr.io images only",
    "llm-docker-compose.yml": "ai_lab — ghcr.io images only",
    "vlm-docker-compose.yml": "ai_lab — ghcr.io images only",
}


def declared_compose_files() -> list[tuple[Path, str]]:
    """Every compose file a device YAML points at, as (device_yaml, name)."""
    found: list[tuple[Path, str]] = []
    for dev in sorted(SOLUTIONS.glob("*/devices/*.y*ml")):
        text = dev.read_text(encoding="utf-8", errors="replace")
        for ref in _COMPOSE_FILE.findall(text):
            found.append((dev.relative_to(ROOT), Path(ref.strip("\"'")).name))
    return found


def main() -> int:
    offenders = [
        (dev, name)
        for dev, name in declared_compose_files()
        if not looks_like_compose_file(name) and name not in _GRANDFATHERED
    ]
    if offenders:
        print("以下 compose 文件名不会被引擎识别，镜像源重写将被静默跳过：\n")
        for dev, name in offenders:
            print(f"  {name}   (declared in {dev})")
        print(
            "\n改成引擎认得的形式："
            "\n  docker-compose.yml / compose.yaml"
            "\n  docker-compose-<限定>.yml   (连字符)"
            "\n  docker-compose.<限定>.yml   (点号)"
            "\n\n不被识别的文件原样上传，公共镜像（mysql、redis 等）会直连"
            "\nDocker Hub，在受限网络下部署超时失败，而日志只报 Pull failed。"
        )
        return 1

    checked = len(declared_compose_files())
    print(f"compose 命名检查通过：{checked} 个声明的 compose 文件都能被镜像源重写覆盖")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

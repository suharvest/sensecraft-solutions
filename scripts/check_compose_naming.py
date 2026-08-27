#!/usr/bin/env python3
"""Fail when a compose file would be skipped by the deployer's mirror rewrite.

The engine only rewrites images to a CN mirror for files whose name it
recognises as a compose file (``docker_remote_deployer._looks_like_compose_file``).
A file the matcher rejects is uploaded verbatim, so public images such as
``mysql:latest`` get pulled straight from Docker Hub — which times out on a
restricted network. The failure surfaces as a bare "Pull failed" during
deployment and points nowhere near the filename, so catch it here instead.

Keep this matcher in sync with the engine's.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS = ROOT / "solutions"


def looks_like_compose_file(name: str) -> bool:
    """Mirror of provisioning_station.deployers.docker_remote_deployer."""
    lower = name.lower()
    if not (lower.endswith(".yml") or lower.endswith(".yaml")):
        return False
    stem = lower.rsplit(".", 1)[0]
    root = stem.split(".", 1)[0]
    if root in ("docker-compose", "compose"):
        return True
    return root.startswith("docker-compose-") or root.startswith("compose-")


def main() -> int:
    offenders: list[tuple[Path, str]] = []
    for path in sorted(SOLUTIONS.glob("*/assets/**/*.y*ml")):
        name = path.name
        # Only judge files that are clearly meant to be compose files.
        if not name.lower().startswith(("docker-compose", "compose")):
            continue
        if not looks_like_compose_file(name):
            offenders.append((path.relative_to(ROOT), name))

    if offenders:
        print("以下 compose 文件名不会被引擎识别，镜像源重写将被静默跳过：\n")
        for rel, name in offenders:
            print(f"  {rel}")
        print(
            "\n改成引擎认得的形式，例如："
            "\n  docker-compose-foo.yml   (连字符限定)"
            "\n  docker-compose.foo.yml   (点号限定)"
            "\n\n背景：不被识别的文件原样上传，公共镜像（mysql、redis 等）"
            "\n会直连 Docker Hub，在受限网络下部署超时失败，"
            "\n而日志只报 Pull failed，指不回文件名。"
        )
        return 1

    print("compose 文件命名检查通过：镜像源重写对全部文件生效")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

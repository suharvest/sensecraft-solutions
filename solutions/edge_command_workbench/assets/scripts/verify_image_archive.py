#!/usr/bin/env python3
"""Verify a docker save archive without extracting it to disk."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile


MAX_METADATA_BYTES = 1024 * 1024


class HashingReader:
    def __init__(self, stream):
        self.stream = stream
        self.hash = hashlib.sha256()

    def read(self, size=-1):
        data = self.stream.read(size)
        if data:
            self.hash.update(data)
        return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", help="archive path, or - for stdin")
    parser.add_argument("--sha256", default=None, help="expected archive SHA256")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--config-sha256", required=True)
    args = parser.parse_args()

    source = sys.stdin.buffer if args.archive == "-" else open(args.archive, "rb")
    reader = HashingReader(source)
    try:
        metadata = {}
        manifest_bytes = None
        with tarfile.open(fileobj=reader, mode="r|*") as archive:
            for member in archive:
                if not member.isfile() or member.size > MAX_METADATA_BYTES:
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    continue
                chunks = []
                remaining = member.size
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError(f"short read for archive member: {member.name}")
                    chunks.append(chunk)
                    remaining -= len(chunk)
                content = b"".join(chunks)
                metadata[member.name] = hashlib.sha256(content).hexdigest()
                if member.name == "manifest.json":
                    manifest_bytes = content
        if manifest_bytes is None:
            raise ValueError("docker archive has no manifest.json")
        manifest = json.loads(manifest_bytes)
        match = next((item for item in manifest if args.tag in (item.get("RepoTags") or [])), None)
        if match is None:
            raise ValueError(f"exact RepoTag not found: {args.tag}")
        config_name = match.get("Config")
        if not config_name:
            raise ValueError("matching manifest entry has no Config")
        config_sha = metadata.get(config_name)
        if config_sha is None:
            raise ValueError(f"config member missing or larger than {MAX_METADATA_BYTES} bytes: {config_name}")
        if config_sha != args.config_sha256:
            raise ValueError(f"config SHA mismatch: {config_sha} (expected {args.config_sha256})")
    finally:
        if args.archive != "-":
            source.close()

    archive_sha = reader.hash.hexdigest()
    if args.sha256 and archive_sha != args.sha256:
        raise SystemExit(
            f"archive SHA mismatch: {archive_sha} (expected {args.sha256})"
        )
    print(json.dumps({"tag": args.tag, "archive_sha256": archive_sha, "config_sha256": args.config_sha256}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, StopIteration, tarfile.TarError, ValueError) as exc:
        print(f"archive verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

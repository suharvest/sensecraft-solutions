"""Offline ``steps`` command — assembled per-preset step view.

A deployment step is authored in two files with different jobs: the guide
heading (``## Step N: … {#id type=… config=…}``) defines the step's
existence, order and user-facing prose, while the ``devices/*.yaml`` it
points at carries the executable payload (firmware source + checksum,
compose file, flash parameters, …). That join is implicit in the sources;
this command prints it explicitly so authors can see at a glance what each
step actually deploys — and review payloads (e.g. firmware checksums)
before release.

Engine-free: only the guide parser + PyYAML, same as ``validate``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Payload fields worth surfacing per deployer family. Dotted paths into the
# device YAML; listed in display order.
_PAYLOAD_FIELDS: tuple[str, ...] = (
    "firmware.source",
    "firmware.language_variants.zh",
    "firmware.language_variants.en",
    "docker.compose_file",
    "docker_remote.compose_file",
    "package.path",
    "package.url",
    "binary.path",
    "binary.url",
    "nodered.flow_file",
    "web_dashboard.url",
    "script.path",
)


def _dig(data, dotted: str):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _fmt(val, limit: int = 140) -> str:
    text = str(val)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _payload_lines(dev_data: dict) -> list[str]:
    lines = []
    for field in _PAYLOAD_FIELDS:
        val = _dig(dev_data, field)
        if val is None:
            continue
        if isinstance(val, dict):
            # e.g. checksum: {sha256: …} or language_variants entries
            # ({path, checksum}) — flatten one level.
            for k, v in val.items():
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        lines.append(f"{field}.{k}.{k2}: {_fmt(v2)}")
                else:
                    lines.append(f"{field}.{k}: {_fmt(v)}")
            continue
        lines.append(f"{field}: {_fmt(val)}")
    return lines


def run(solution_path: str, lang: str = "en", spec_dir: str | None = None) -> int:
    """Print the assembled preset → step → payload view. 0 unless the guide
    is missing/unparseable."""
    import yaml

    from sensecraft_solution_spec import markdown_parser as mp

    from .validate import _find_spec_dir

    sol_path = Path(solution_path).expanduser()
    if not sol_path.is_dir():
        print(f"Error: solution path not found: {sol_path}", file=sys.stderr)
        return 1

    # Seed valid step types from capabilities.json when available so plugin /
    # non-default types parse; fall back to accepting whatever is present.
    spec = _find_spec_dir(sol_path, spec_dir)
    if spec is not None and (spec / "capabilities.json").is_file():
        import json

        caps = json.loads((spec / "capabilities.json").read_text(encoding="utf-8"))
        deployer_keys = set((caps.get("deployers") or {}).keys())
        mp.register_step_type_provider(lambda: deployer_keys)

    guide_name = "guide_zh.md" if lang == "zh" else "guide.md"
    guide_path = sol_path / guide_name
    if not guide_path.is_file():
        print(f"Error: {guide_name} not found in {sol_path}", file=sys.stderr)
        return 1

    result = mp.parse_single_language_guide(
        guide_path.read_text(encoding="utf-8"), lang
    )
    for perr in result.errors:
        print(f"parse: {perr}", file=sys.stderr)

    for preset in result.presets:
        pname = preset.name.get(lang) or preset.id
        print(f"\n━━ Preset: {pname}  {{#{preset.id}}}")
        for i, step in enumerate(preset.steps, 1):
            title = step.section.title.get(lang) or step.title.get(lang) or step.id
            req = "" if step.required else "  (optional)"
            print(f"  {i}. {title}  {{#{step.id}}}  type={step.type}{req}")
            if not step.config_file:
                print("       payload: (none — manual/prose-only step)")
                continue
            cfg_path = sol_path / step.config_file
            print(f"       config: {step.config_file}")
            if not cfg_path.is_file():
                print("       payload: ✗ CONFIG FILE MISSING")
                continue
            try:
                dev_data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                print(f"       payload: ✗ YAML parse error: {exc}")
                continue
            for line in _payload_lines(dev_data if isinstance(dev_data, dict) else {}):
                print(f"       {line}")
            for target in step.targets or []:
                tcfg = f"  config={target.config_file}" if target.config_file else ""
                print(f"       target: #{target.id} ({target.target_type}){tcfg}")
    print()
    return 0

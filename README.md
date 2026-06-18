# SenseCraft Solutions

Open solution content and authoring tooling for the **SenseCraft Solution**
provisioning platform — the IoT deployment solutions shipped in the SenseCraft
desktop app, plus the tools to write and validate your own.

The provisioning **engine** (deployers, device communication, desktop app) is
closed-source and distributed as a signed binary. This repository is the open
**content + contract + tooling** layer; everything here is Apache-2.0.

## Layout

| Path | What |
|------|------|
| `solutions/` | Solution packages — `solution.yaml`, bilingual `guide.md`/`description.md`, device configs, assets |
| `spec/` | Generated contract: JSON Schema + `CONTRACT.md` (field rules, `docker_deploy` derivation, guide syntax) |
| `packages/sensecraft-solution-spec/` | `guide.md` parser primitives (PyPI) |
| `packages/solutionctl/` | Offline validator + thin client that drives the installed engine binary (PyPI) |
| `skills/` | Authoring playbooks (copywriting, docker/firmware prep) |
| `scripts/` | CI boundary guard (`public-repo-guard.sh`) |

## Quick start

```bash
uv sync

# Validate a solution offline (no engine needed):
uv run --package sensecraft-solutionctl solutionctl validate solutions/<id>

# With the SenseCraft desktop app installed, deploy headlessly:
uv run --package sensecraft-solutionctl solutionctl deploy <id> --connection '{...}'
```

`solutionctl` locates the installed engine binary automatically (env override →
`~/.sensecraft/engine.json` handshake → platform-native lookup).

## Writing a solution

See [`spec/CONTRACT.md`](spec/CONTRACT.md) for the authoritative field/syntax
rules and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow. AI agents:
see [`AGENTS.md`](AGENTS.md).

## Notes

- Solution `docker-compose` files use **demo default credentials** (e.g. local
  InfluxDB tokens). These are not secrets; change them for production.
- Container images are pulled from public registries.

## License

[Apache-2.0](LICENSE).

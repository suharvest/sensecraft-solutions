# Contributing

Thanks for contributing SenseCraft solutions and tooling improvements!

## What lives here

- `solutions/` — solution content (YAML config, bilingual Markdown guides, assets).
- `spec/` — the machine-readable contract (JSON Schema + `CONTRACT.md`) the
  SenseCraft engine validates solutions against. **Generated; do not hand-edit.**
- `packages/` — `sensecraft-solution-spec` (guide parser) and `solutionctl`
  (offline validator + thin client).
- `skills/` — authoring playbooks.

## Authoring / validating a solution

```bash
uv sync
uv run --package sensecraft-solutionctl solutionctl validate solutions/<your_solution>
```

Read `spec/CONTRACT.md` for the field rules, `docker_deploy` view-derivation,
path resolution, and `guide.md` Step/Target syntax. Start from
`skills/solution-copywriting` and the `prepare-*` skills.

## Pull requests

1. Keep one solution (or one focused change) per PR.
2. `solutionctl validate` must pass; `uv run pytest tests/test_solution_format.py` green.
3. Use public container images. Demo credentials in compose files are **demo
   defaults** — never put real secrets in a solution.

## How your PR is checked and merged

CI runs automatically on every PR. **`guard` and `validate` must be green to
merge** (enforced by branch protection); `docker-smoke` runs on solution changes
and should be green too:

| Check | What it gates |
|-------|---------------|
| `guard` | Open/closed boundary (no engine internals leak into this repo). |
| `validate` | `solutionctl validate --check-urls` on every solution — schema, referenced files exist, i18n completeness, duplicate ids, device-ref integrity, dead-link (4xx) detection, compose/flow parseability, ≥1 verify step per preset, EN/ZH structure parity, and `verified:` claim consistency. |
| `docker-smoke` | For presets that opt in with `docker.ci_smoke: true`, brings the compose stack up on a CI runner and checks each declared service's health endpoint — proves the solution **can deploy**. |

**What CI does NOT check** (and the maintainer reviews by hand):
- **Rendering** — that your solution looks right in the app (no broken images,
  no leaked `{#...}` markers). Run `solutionctl validate` + preview via the
  desktop app's import feature; the maintainer also runs an internal
  render-health check before merge.
- **Output correctness** — whether the deployed thing actually *works right*
  (model accuracy, voice quality). This is never auto-verified; mark a preset
  `verified: [hardware]` only after a real on-device run.

After merge, the maintainer pulls the change into the engine and ships it to
installed apps over the air — no app reinstall needed.

## Developer Certificate of Origin (DCO)

By contributing, you certify the [DCO](https://developercertificate.org/). Sign
off every commit:

```bash
git commit -s -m "your message"
```

This adds a `Signed-off-by: Your Name <you@example.com>` trailer.

## License

Contributions are licensed under **Apache-2.0** (see `LICENSE`).

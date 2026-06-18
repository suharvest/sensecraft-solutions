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
uv run --package solutionctl solutionctl validate solutions/<your_solution>
```

Read `spec/CONTRACT.md` for the field rules, `docker_deploy` view-derivation,
path resolution, and `guide.md` Step/Target syntax. Start from
`skills/solution-copywriting` and the `prepare-*` skills.

## Pull requests

1. Keep one solution (or one focused change) per PR.
2. `solutionctl validate` must pass; `uv run pytest tests/unit/test_solution_format.py` green.
3. Use public container images. Demo credentials in compose files are **demo
   defaults** — never put real secrets in a solution.

## Developer Certificate of Origin (DCO)

By contributing, you certify the [DCO](https://developercertificate.org/). Sign
off every commit:

```bash
git commit -s -m "your message"
```

This adds a `Signed-off-by: Your Name <you@example.com>` trailer.

## License

Contributions are licensed under **Apache-2.0** (see `LICENSE`).

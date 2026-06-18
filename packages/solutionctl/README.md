# solutionctl

Thin public-side client for the (closed-source) **SenseCraft Solution** engine
binary. `solutionctl` contains **zero engine code** — it only locates the
installed engine binary and drives it via `subprocess` / local REST.

## How it finds the engine

Three-level resolution (`solutionctl.engine_locator`):

1. `$SENSECRAFT_ENGINE_BIN` environment variable
2. `~/.sensecraft/engine.json` handshake file (written by the desktop App on
   startup)
3. Platform-native discovery:
   - **macOS**: `mdfind` by bundle identifier, with `/Applications` fallback
   - **Windows**: `Uninstall` registry keys (`InstallLocation`)
   - **Linux**: `dpkg -L sensecraft-solution`

Each candidate is validated (`is_file` + executable + PyInstaller onedir
`_internal` sibling) before being accepted.

## Commands

- `solutionctl deploy <id> [...]` — drive `<engine> deploy <id> --json`,
  render the NDJSON event stream.
- `solutionctl manage list-apps` — start `<engine> serve --headless`, poll
  health, query the REST API, then shut the server down.
- `solutionctl meta` — print engine metadata (`<engine> meta --json`).

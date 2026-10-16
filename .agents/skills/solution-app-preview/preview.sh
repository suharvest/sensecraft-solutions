#!/usr/bin/env bash
#
# solution-app-preview — bridge this sensecraft-solutions working repo and the
# SenseCraft Solution engine app (app_collaboration) for two scenarios:
#
#   preview  →  LOCAL DEV (fast): run the dev app pointed straight at this working
#               repo via PS_SOLUTIONS_DIR. No sync, no submodule touch; edits
#               (even uncommitted) show on refresh.
#   bind     →  PUBLISH: move the app's `sensecraft-solutions` submodule pointer
#               to this repo's HEAD commit (fetched locally). Warns if that commit
#               isn't on origin yet (push solutions before the app submodule bump
#               is publishable).
#
# The two are orthogonal: `preview` is a runtime override that never dirties the
# submodule; `bind` is the source-of-truth pin used at release time.
#
# Paths: SRC (this repo) is derived from the script location. The app repo
# defaults to a sibling `../app_collaboration`; override with PS_APP. SRC is
# overridable with PS_SRC.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${PS_SRC:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
APP="${PS_APP:-$(cd "$SRC/.." && pwd)/app_collaboration}"
SUB="$APP/sensecraft-solutions"

die() { echo "error: $*" >&2; exit 1; }

[ -d "$SRC/solutions" ] || die "working repo not found: $SRC/solutions (set PS_SRC)"
[ -d "$APP" ]           || die "app repo not found: $APP (set PS_APP)"

cmd="${1:-help}"; shift || true

case "$cmd" in
  preview|dev|run)
    # Fast local preview: dev app reads this working repo directly.
    [ -x "$APP/dev.sh" ] || die "$APP/dev.sh not found/executable"
    echo ">> dev app → PS_SOLUTIONS_DIR=$SRC/solutions (submodule untouched)"
    echo ">> editing $SRC/solutions and refreshing the app shows changes live"
    exec env PS_SOLUTIONS_DIR="$SRC/solutions" "$APP/dev.sh"
    ;;

  env)
    # Just print the export line, for pasting into your own launch flow.
    echo "export PS_SOLUTIONS_DIR=$SRC/solutions"
    ;;

  bind|sync)
    # Publish binding: point the submodule at this repo's HEAD (or given ref).
    ref="${1:-HEAD}"
    [ -e "$SUB/.git" ] || die "submodule not initialised: $SUB"
    sha="$(git -C "$SRC" rev-parse "$ref")"
    branch="$(git -C "$SRC" rev-parse --abbrev-ref HEAD)"
    echo ">> fetching $branch ($sha) from $SRC into submodule"
    git -C "$SUB" fetch -q "$SRC" "$branch"
    git -C "$SUB" checkout -q "$sha"
    echo ">> submodule now at: $(git -C "$SUB" rev-parse --short HEAD)"
    if git -C "$SRC" branch -r --contains "$sha" 2>/dev/null | grep -q origin; then
      echo ">> $sha is on origin — safe to commit the submodule bump in the app repo"
    else
      echo "!! WARNING: $sha is NOT on origin. For a real publish, push solutions first:"
      echo "     git -C $SRC push origin $branch"
      echo "   then commit the app submodule bump:"
      echo "     git -C $APP add sensecraft-solutions && git -C $APP commit -m 'chore: bump solutions submodule'"
    fi
    ;;

  restore|reset)
    # Revert the submodule to whatever commit the app repo pins.
    git -C "$APP" submodule update --checkout --force sensecraft-solutions
    echo ">> submodule restored to app-pinned commit: $(git -C "$APP" submodule status sensecraft-solutions)"
    ;;

  status)
    echo "working repo ($SRC):"
    echo "  HEAD: $(git -C "$SRC" rev-parse --short HEAD) [$(git -C "$SRC" rev-parse --abbrev-ref HEAD)]"
    echo "app submodule pin ($APP):"
    echo "  $(git -C "$APP" submodule status sensecraft-solutions)"
    ;;

  *)
    cat <<EOF
solution-app-preview — local preview + submodule bind

usage: preview.sh <command>

  preview        run the dev app pointed at this working repo (fast, no sync)
  env            print the PS_SOLUTIONS_DIR export line
  bind [ref]     point the app submodule at this repo's HEAD (publish)
  restore        revert the submodule to the app-pinned commit
  status         show working-repo HEAD and app submodule pin

paths: SRC=$SRC
       APP=$APP   (override with PS_APP)
EOF
    ;;
esac

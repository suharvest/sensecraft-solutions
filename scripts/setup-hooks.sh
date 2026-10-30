#!/usr/bin/env bash
# Setup git hooks to point to repository-versioned .githooks directory.
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CURRENT_HOOKS=$(git config --local core.hooksPath || true)

if [ "$CURRENT_HOOKS" = ".githooks" ]; then
    echo "✅ Git hooks already configured to .githooks"
    exit 0
fi

if [ -n "$CURRENT_HOOKS" ]; then
    echo "⚠️  Existing core.hooksPath found: $CURRENT_HOOKS"
    echo "   Overriding with local repository hooks at .githooks..."
fi

git config --local core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

echo "✅ Successfully configured Git hooks to .githooks"
echo "   - pre-commit: fast offline lint and contract check (~2s)"
echo "   - pre-push:   full offline validation (tests + solutions schema)"

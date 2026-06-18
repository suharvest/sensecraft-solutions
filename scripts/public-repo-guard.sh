#!/bin/sh
# Public-repo boundary guard. Fails if closed-engine source, internal infra,
# credentials, internal docs, or non-whitelisted skills leak into this repo.
# Run in CI on every push/PR.
set -e
fail() { echo "GUARD FAIL: $1"; exit 1; }

# 1. No closed engine / desktop-shell source.
if git ls-files | grep -E '^(provisioning_station|src-tauri|frontend)/' >/dev/null; then
  fail "closed engine/frontend source present"
fi

# 2. No imports of the closed engine (incl. inside packages).
if grep -rE 'import[[:space:]]+provisioning_station|from[[:space:]]+provisioning_station' --include='*.py' . >/dev/null; then
  fail "provisioning_station import found"
fi

# 3. No internal infra hostnames / credential markers.
#    (Device default passwords like 'recamera' are NOT internal infra.)
if grep -rniE '100\.(7[0-9]|8[0-9])\.[0-9]+\.[0-9]+|34\.219\.208\.30|AC_PASSWORD|ossutil|docker[[:space:]]+login[[:space:]]+sensecraft-missionpack' . \
     --include='*.md' --include='*.py' --include='*.yaml' --include='*.yml' >/dev/null; then
  fail "internal infra/credential marker found"
fi

# 4. No internal publishing docs / build artifacts.
if find . -path ./.git -prune -o -name 'IMPORT.md' -print | grep . >/dev/null; then
  fail "IMPORT.md (internal push instructions) present"
fi
if find . -path ./.git -prune -o -type d -name dist -print | grep . >/dev/null; then
  fail "dist/ build artifact present"
fi

# 5. No non-whitelisted (internal) skills.
for s in solution-validation integrate-jetson-solution solution-assets solution \
         test-tauri-windows debug-frontend release-notes; do
  if [ -d "skills/$s" ]; then fail "internal skill '$s' present"; fi
done

echo "GUARD PASS"

#!/usr/bin/env bash
# Build rehab-posture-analysis .deb package for reCamera SG2002 (riscv64)
set -euo pipefail

PKG="rehab-posture-analysis"
VERSION="${1:-1.0.0}"
ARCH="${2:-riscv64}"

SOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGING_DIR="$SOL_DIR/packaging/recamera-deb"
DIST_DIR="$SOL_DIR/dist"
STAGE_DIR="$DIST_DIR/.stage-$PKG-$VERSION-$ARCH"

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1757203200}"

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$@"
    else
        shasum -a 256 "$@"
    fi
}

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "dpkg-deb not found. Please install dpkg." >&2
    exit 1
fi

mkdir -p "$DIST_DIR"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

# Stage all files from packaging/recamera-deb
cp -R "$PACKAGING_DIR/." "$STAGE_DIR/"

# Update version and arch in control if needed
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGE_DIR/DEBIAN/control"
sed -i "s/^Architecture:.*/Architecture: $ARCH/" "$STAGE_DIR/DEBIAN/control"

# Update version in manifests
if [ -f "$STAGE_DIR/userdata/local/apps/$PKG.json" ]; then
    sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$STAGE_DIR/userdata/local/apps/$PKG.json"
fi
if [ -f "$STAGE_DIR/usr/share/$PKG/$PKG.json" ]; then
    sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$STAGE_DIR/usr/share/$PKG/$PKG.json"
fi

# Set permissions
chmod 0755 "$STAGE_DIR/DEBIAN"
chmod 0644 "$STAGE_DIR/DEBIAN/control"
chmod 0755 "$STAGE_DIR/DEBIAN/postinst"
chmod 0755 "$STAGE_DIR/DEBIAN/prerm"
chmod 0755 "$STAGE_DIR/DEBIAN/postrm"
chmod 0755 "$STAGE_DIR/etc/init.d/K92$PKG"
chmod 0755 "$STAGE_DIR/usr/local/bin/$PKG"
chmod 0644 "$STAGE_DIR/usr/share/$PKG/app.conf.default"
chmod 0644 "$STAGE_DIR/usr/share/$PKG/$PKG.json"
chmod 0644 "$STAGE_DIR/usr/share/supervisor/www/apps/$PKG.png"
chmod 0644 "$STAGE_DIR/userdata/local/apps/$PKG.json"

# Pin timestamps for reproducibility
python3 - "$STAGE_DIR" <<'PY'
import os, sys
epoch = int(os.environ["SOURCE_DATE_EPOCH"])
for root, dirs, files in os.walk(sys.argv[1]):
    for name in dirs + files:
        os.utime(os.path.join(root, name), (epoch, epoch), follow_symlinks=False)
os.utime(sys.argv[1], (epoch, epoch))
PY

DEB_FILE="$DIST_DIR/${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb -Zgzip --root-owner-group --build "$STAGE_DIR" "$DEB_FILE" >/dev/null

rm -rf "$STAGE_DIR"

(cd "$DIST_DIR" && sha256 "$(basename "$DEB_FILE")" > "${PKG}_${VERSION}_${ARCH}.sha256")

echo "Package successfully built: $DEB_FILE"

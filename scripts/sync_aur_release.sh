#!/usr/bin/env bash
set -euo pipefail

AUR_PACKAGE="${AUR_PACKAGE:-farmmod}"
UPSTREAM_REPO="${UPSTREAM_REPO:-henriquejsza/FarmMod}"
VERSION="${VERSION:-$(python - <<'PY'
from pathlib import Path
import tomllib

data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
print(data["project"]["version"])
PY
)}"

TARBALL_URL="https://github.com/${UPSTREAM_REPO}/archive/refs/tags/v${VERSION}.tar.gz"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

curl -fsSL "$TARBALL_URL" -o "$WORKDIR/source.tar.gz"
SHA256="$(sha256sum "$WORKDIR/source.tar.gz" | cut -d' ' -f1)"

git clone "ssh://aur@aur.archlinux.org/${AUR_PACKAGE}.git" "$WORKDIR/aur"

cat >"$WORKDIR/aur/PKGBUILD" <<EOF
pkgname=${AUR_PACKAGE}
pkgver=${VERSION}
pkgrel=1
pkgdesc="Mod manager for Farming Simulator on Linux"
arch=("any")
url="https://github.com/${UPSTREAM_REPO}"
license=("AGPL-3.0-or-later")
depends=(
  "python"
  "python-gobject"
  "gtk4"
  "libadwaita"
)
makedepends=(
  "python-build"
  "python-installer"
  "python-setuptools"
  "python-wheel"
)
checkdepends=(
  "python-pytest"
)
provides=("farmmod-hub")
conflicts=("farmmod-hub")
replaces=("farmmod-hub")

_srcdir="FarmMod-\$pkgver"
source=("\$pkgname-\$pkgver.tar.gz::https://github.com/${UPSTREAM_REPO}/archive/refs/tags/v\$pkgver.tar.gz")
sha256sums=("${SHA256}")

build() {
  cd "\$srcdir/\$_srcdir"
  python -m build --wheel --no-isolation
}

check() {
  cd "\$srcdir/\$_srcdir"
  pytest
}

package() {
  cd "\$srcdir/\$_srcdir"

  python -m installer --destdir="\$pkgdir" dist/*.whl

  _python_stdlib=\$(python - <<'PY'
import sysconfig
print(sysconfig.get_path("stdlib"))
PY
)

  if [[ -x "\$pkgdir/usr/bin/farmmod-hub" && ! -x "\$pkgdir/usr/bin/farmmod" ]]; then
    ln -s "farmmod-hub" "\$pkgdir/usr/bin/farmmod"
  fi

  install -Dm644 "LICENSE" "\$pkgdir/usr/share/licenses/\$pkgname/LICENSE"
  install -Dm644 "AUTHORS" "\$pkgdir/usr/share/licenses/\$pkgname/AUTHORS"

  install -Dm644 \
    "packaging/io.github.henriquejsza.farmmod-hub.desktop" \
    "\$pkgdir/usr/share/applications/io.github.henriquejsza.farmmod-hub.desktop"

  install -Dm644 \
    "data/logo/io.github.henriquejsza.farmmod-hub.png" \
    "\$pkgdir/usr/share/icons/hicolor/512x512/apps/io.github.henriquejsza.farmmod-hub.png"
  install -Dm644 \
    "data/logo/io.github.henriquejsza.farmmod-hub.png" \
    "\$pkgdir/usr/share/icons/hicolor/256x256/apps/io.github.henriquejsza.farmmod-hub.png"
  install -Dm644 \
    "data/logo/io.github.henriquejsza.farmmod-hub.png" \
    "\$pkgdir/usr/share/icons/hicolor/128x128/apps/io.github.henriquejsza.farmmod-hub.png"

  install -Dm644 \
    "data/style.css" \
    "\$pkgdir/usr/share/farmmod/data/style.css"
  install -Dm644 \
    "data/logo/io.github.henriquejsza.farmmod-hub.png" \
    "\$pkgdir/usr/share/farmmod/data/logo/io.github.henriquejsza.farmmod-hub.png"

  install -Dm644 \
    "data/style.css" \
    "\$pkgdir\$_python_stdlib/data/style.css"
  install -Dm644 \
    "data/logo/io.github.henriquejsza.farmmod-hub.png" \
    "\$pkgdir\$_python_stdlib/data/logo/io.github.henriquejsza.farmmod-hub.png"
}
EOF

(
  cd "$WORKDIR/aur"
  makepkg --printsrcinfo > .SRCINFO
  git add PKGBUILD .SRCINFO
  if git diff --staged --quiet; then
    echo "No AUR changes to push."
    exit 0
  fi

  git commit -m "Update to v${VERSION}"
  git push origin master
)

echo "AUR package ${AUR_PACKAGE} updated to ${VERSION}."

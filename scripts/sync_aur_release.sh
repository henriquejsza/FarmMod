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
SOURCE_ARCHIVE_PATH="${SOURCE_ARCHIVE_PATH:-refs/tags/v${VERSION}}"
SRC_DIRNAME="${SRC_DIRNAME:-FarmMod-${VERSION}}"

TARBALL_URL="https://github.com/${UPSTREAM_REPO}/archive/${SOURCE_ARCHIVE_PATH}.tar.gz"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

curl -fsSL "$TARBALL_URL" -o "$WORKDIR/source.tar.gz"
SHA256="$(sha256sum "$WORKDIR/source.tar.gz" | cut -d' ' -f1)"

git clone "ssh://aur@aur.archlinux.org/${AUR_PACKAGE}.git" "$WORKDIR/aur"

CURRENT_PKGVER=""
CURRENT_PKGREL=""
CURRENT_SHA256=""
if [[ -f "$WORKDIR/aur/PKGBUILD" ]]; then
  CURRENT_PKGVER="$(grep -E '^pkgver=' "$WORKDIR/aur/PKGBUILD" | head -n1 | cut -d= -f2-)"
  CURRENT_PKGREL="$(grep -E '^pkgrel=' "$WORKDIR/aur/PKGBUILD" | head -n1 | cut -d= -f2-)"
  CURRENT_SHA_LINE="$(grep -E '^sha256sums=' "$WORKDIR/aur/PKGBUILD" | head -n1 || true)"
  CURRENT_SHA256="${CURRENT_SHA_LINE#sha256sums=(\"}"
  CURRENT_SHA256="${CURRENT_SHA256%\")}" 
fi

PKGREL=1
if [[ "$CURRENT_PKGVER" == "$VERSION" ]]; then
  if [[ -n "$CURRENT_SHA256" && "$CURRENT_SHA256" == "$SHA256" ]]; then
    PKGREL="${CURRENT_PKGREL:-1}"
  else
    PKGREL="$(( ${CURRENT_PKGREL:-0} + 1 ))"
  fi
fi

cat >"$WORKDIR/aur/PKGBUILD" <<EOF
pkgname=${AUR_PACKAGE}
pkgver=${VERSION}
pkgrel=${PKGREL}
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

_srcdir="${SRC_DIRNAME}"
source=("\$pkgname-\$pkgver.tar.gz::${TARBALL_URL}")
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
  cat > .SRCINFO <<EOF
pkgbase = ${AUR_PACKAGE}
	pkgdesc = Mod manager for Farming Simulator on Linux
	pkgver = ${VERSION}
	pkgrel = ${PKGREL}
	url = https://github.com/${UPSTREAM_REPO}
	arch = any
	license = AGPL-3.0-or-later
	checkdepends = python-pytest
	makedepends = python-build
	makedepends = python-installer
	makedepends = python-setuptools
	makedepends = python-wheel
	depends = python
	depends = python-gobject
	depends = gtk4
	depends = libadwaita
	provides = farmmod-hub
	conflicts = farmmod-hub
	replaces = farmmod-hub
	source = ${AUR_PACKAGE}-${VERSION}.tar.gz::${TARBALL_URL}
	sha256sums = ${SHA256}

pkgname = ${AUR_PACKAGE}
EOF
  git add PKGBUILD .SRCINFO
  if git diff --staged --quiet; then
    echo "No AUR changes to push."
    exit 0
  fi

  git commit -m "Update to v${VERSION}"
  git push origin master
)

echo "AUR package ${AUR_PACKAGE} updated to ${VERSION}."

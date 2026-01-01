#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="v0.7.0"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64|amd64)
    ARCH="amd64"
    ;;
  arm64|aarch64)
    ARCH="arm64"
    ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

BIN_DIR="$ROOT/scripts/.cache/kubeconform/$VERSION/$OS-$ARCH"
BIN="$BIN_DIR/kubeconform"

if [[ ! -x "$BIN" ]]; then
  mkdir -p "$BIN_DIR"
  URL="https://github.com/yannh/kubeconform/releases/download/${VERSION}/kubeconform-${OS}-${ARCH}.tar.gz"
  TAR="$BIN_DIR/$(basename "$URL")"
  CHECKSUMS="$BIN_DIR/CHECKSUMS"
  curl -sSL -o "$TAR" "$URL"
  curl -sSL -o "$CHECKSUMS" "https://github.com/yannh/kubeconform/releases/download/${VERSION}/CHECKSUMS"

  if command -v sha256sum >/dev/null 2>&1; then
    grep "$(basename "$TAR")" "$CHECKSUMS" | (cd "$BIN_DIR" && sha256sum --check)
  elif command -v shasum >/dev/null 2>&1; then
    grep "$(basename "$TAR")" "$CHECKSUMS" | (cd "$BIN_DIR" && shasum -a 256 -c)
  else
    echo "sha256sum or shasum is required to verify kubeconform" >&2
    exit 1
  fi
  tar -xz -C "$BIN_DIR" -f "$TAR"
  chmod +x "$BIN"
  rm -f "$TAR" "$CHECKSUMS"
fi

find apps infrastructure bootstrap -name "*.yaml" ! -name "app.yaml" ! -name ".argocd-source-*.yaml" -print0 \
  | xargs -0 "$BIN" -kubernetes-version 1.35.0 -strict -ignore-missing-schemas -summary

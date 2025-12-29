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
  curl -sSL "$URL" | tar -xz -C "$BIN_DIR"
  chmod +x "$BIN"
fi

find apps infrastructure bootstrap -name "*.yaml" ! -name "app.yaml" ! -name ".argocd-source-*.yaml" -print0 \
  | xargs -0 "$BIN" -kubernetes-version 1.35.0 -strict -ignore-missing-schemas -summary

#!/usr/bin/env bash
#
# dev-container.sh - Ubuntu 26.04 workstation in Apple Containers
#
# Usage:
#   ./scripts/dev-container.sh up      # Create + provision the workstation
#   ./scripts/dev-container.sh shell   # Open a shell inside
#   ./scripts/dev-container.sh down    # Stop + remove the workstation
#
# Environment:
#   DEV_CPUS    CPUs for the container (default 4)
#   DEV_MEMORY  memory for the container (default 8G)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

DEV_NAME="${DEV_NAME:-homelab-dev}"
DEV_CPUS="${DEV_CPUS:-4}"
DEV_MEMORY="${DEV_MEMORY:-8G}"
DEV_IMAGE="${DEV_IMAGE:-docker.io/library/ubuntu:26.04}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

container_running() {
    container list 2>/dev/null | grep -q "^${DEV_NAME} "
}

cmd_up() {
    command -v container >/dev/null 2>&1 || { log_error "Apple container CLI not found (brew install container)"; exit 1; }
    if container_running; then
        log_info "Container $DEV_NAME already running"
    else
        log_info "Creating Ubuntu 26.04 workstation..."
        container run -d --name "$DEV_NAME" \
            --cap-add ALL --masked-path NONE \
            -c "$DEV_CPUS" -m "$DEV_MEMORY" \
            -v "$REPO_ROOT:/homelab" \
            "$DEV_IMAGE" sleep infinity
    fi
    log_info "Provisioning tooling (Docker, talosctl, kubectl)..."
    container exec "$DEV_NAME" bash -c "mount -o remount,rw /proc/sys 2>/dev/null; echo 1 > /proc/sys/net/ipv4/ip_forward"
    container exec "$DEV_NAME" bash -c "command -v docker >/dev/null || (apt-get update && apt-get install -y docker.io curl ca-certificates)"
    TALOS_VERSION="$(grep -E '^talosctl:' "$REPO_ROOT/talos/versions.yaml" | awk '{print $2}')"
    K8S_VERSION="$(grep -E '^kubernetes:' "$REPO_ROOT/talos/versions.yaml" | awk '{print $2}')"
    ARCH="$(container exec "$DEV_NAME" uname -m | tr -d '[:space:]')"
    [[ "$ARCH" == "aarch64" ]] && TARCH="arm64" || TARCH="amd64"
    container exec "$DEV_NAME" bash -c "command -v talosctl >/dev/null || (curl -sSL -o /usr/local/bin/talosctl https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/talosctl-linux-${TARCH} && chmod +x /usr/local/bin/talosctl)"
    container exec "$DEV_NAME" bash -c "command -v kubectl >/dev/null || (curl -sSL -o /usr/local/bin/kubectl https://dl.k8s.io/release/v${K8S_VERSION}/bin/linux/${TARCH}/kubectl && chmod +x /usr/local/bin/kubectl)"
    container exec "$DEV_NAME" bash -c "pgrep dockerd >/dev/null || (nohup dockerd > /tmp/dockerd.log 2>&1 & sleep 8)"
    container exec "$DEV_NAME" docker info --format 'Docker {{.ServerVersion}} ready'
    log_success "Workstation ready at /homelab - open with: $0 shell"
}

cmd_shell() {
    container_running || { log_error "Container not running - run $0 up first"; exit 1; }
    container exec -it "$DEV_NAME" bash -c "cd /homelab && exec bash"
}

cmd_down() {
    if container_running; then
        container stop "$DEV_NAME" 2>/dev/null || true
    fi
    container delete --force "$DEV_NAME" 2>/dev/null || true
    log_success "Workstation removed"
}

case "${1:-help}" in
    up) cmd_up ;;
    shell) cmd_shell ;;
    down) cmd_down ;;
    *) echo "Usage: $0 {up|shell|down}"; exit 1 ;;
esac

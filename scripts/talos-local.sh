#!/usr/bin/env bash
#
# talos-local.sh - Local Talos QEMU rehearsal cluster
#
# Usage:
#   ./scripts/talos-local.sh up      # Create the rehearsal cluster
#   ./scripts/talos-local.sh down    # Destroy the rehearsal cluster
#   ./scripts/talos-local.sh status  # Show cluster status
#
# Environment:
#   WORKER_COUNT  number of workers (default 1)
#   CP_CPUS       control plane CPUs (default 4)
#   CP_MEMORY     control plane memory (default 4G)
#   CP_DISK       control plane disk MB (default 10240)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
WORK_DIR="$REPO_ROOT/talos/.rehearsal"
KUBECONFIG_PATH="$WORK_DIR/kubeconfig"

WORKER_COUNT="${WORKER_COUNT:-1}"
CP_CPUS="${CP_CPUS:-4}"
CP_MEMORY="${CP_MEMORY:-4G}"
CP_DISK="${CP_DISK:-10240}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    log_info "Checking prerequisites..."
    local missing=()
    command -v talosctl >/dev/null 2>&1 || missing+=("talosctl")
    command -v kubectl >/dev/null 2>&1 || missing+=("kubectl")
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi
    log_success "All prerequisites installed"
}

read_versions() {
    TALOS_VERSION="$(grep -E '^talos:' "$REPO_ROOT/talos/versions.yaml" | awk '{print $2}')"
    K8S_VERSION="$(grep -E '^kubernetes:' "$REPO_ROOT/talos/versions.yaml" | awk '{print $2}')"
    export TALOS_VERSION="v${TALOS_VERSION#v}"
    export K8S_VERSION="${K8S_VERSION#v}"
}

cluster_up() {
    echo ""
    echo "=========================================="
    echo "   Homelab Local Talos Cluster"
    echo "=========================================="
    echo ""
    check_prerequisites
    read_versions
    mkdir -p "$WORK_DIR"
    log_info "Creating QEMU rehearsal cluster (this downloads images on first run)..."
    cd "$WORK_DIR"
    sudo -E talosctl cluster create dev \
        --workers "$WORKER_COUNT" \
        --cpus "$CP_CPUS" \
        --memory "$CP_MEMORY" \
        --disk "$CP_DISK" \
        --kubernetes-version "$K8S_VERSION" \
        --talos-version "$TALOS_VERSION"
    cd "$REPO_ROOT"
    cp "$WORK_DIR/_out/kubeconfig" "$KUBECONFIG_PATH" 2>/dev/null || true
    run_smoke_test
    echo ""
    echo "=========================================="
    echo "   Cluster Ready!"
    echo "=========================================="
    echo ""
    echo "KUBECONFIG: $KUBECONFIG_PATH"
    echo ""
    echo "Quick commands:"
    echo "  export KUBECONFIG=$KUBECONFIG_PATH"
    echo "  kubectl get nodes"
    echo "  kubectl get pods -A"
    echo ""
    echo "To destroy: ./scripts/talos-local.sh down"
    echo ""
}

run_smoke_test() {
    log_info "Running smoke test..."
    export KUBECONFIG="$KUBECONFIG_PATH"
    kubectl apply -f "$REPO_ROOT/talos/test/deployment.yaml"
    kubectl apply -f "$REPO_ROOT/talos/test/service.yaml"
    kubectl wait --for=condition=ready pod -l app=test-nginx --timeout=180s
    log_success "Smoke test passed!"
}

cluster_down() {
    log_info "Destroying local cluster..."
    cd "$WORK_DIR" 2>/dev/null || exit 0
    sudo -E talosctl cluster destroy --provisioner qemu || true
    cd "$REPO_ROOT"
    rm -rf "$WORK_DIR"
    log_success "Cluster destroyed"
}

cluster_status() {
    echo ""
    if [[ -f "$KUBECONFIG_PATH" ]]; then
        echo "Kubernetes Status:"
        kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes -o wide 2>/dev/null || echo "  Cannot connect to cluster"
        echo ""
    else
        echo "No kubeconfig found at $KUBECONFIG_PATH"
    fi
}

case "${1:-help}" in
    up)
        cluster_up
        ;;
    down)
        cluster_down
        ;;
    status)
        cluster_status
        ;;
    *)
        echo "Usage: $0 {up|down|status}"
        exit 1
        ;;
esac

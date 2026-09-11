#!/usr/bin/env bash
#
# talos-baremetal.sh - Zero-touch Talos Linux bare-metal lifecycle
#
# Usage:
#   ./scripts/talos-baremetal.sh iso-url                 Print installer ISO + image URLs
#   ./scripts/talos-baremetal.sh up                      Full flow: secrets, config, apply, bootstrap, kubeconfig, ArgoCD
#   ./scripts/talos-baremetal.sh gen-secrets              Generate cluster secrets once
#   ./scripts/talos-baremetal.sh gen-config               Render per-node machine configs
#   ./scripts/talos-baremetal.sh apply [--role R] [--limit HOST]
#   ./scripts/talos-baremetal.sh bootstrap                Bootstrap etcd on first control plane
#   ./scripts/talos-baremetal.sh kubeconfig                Fetch kubeconfig
#   ./scripts/talos-baremetal.sh upgrade-talos             Roll Talos OS upgrades
#   ./scripts/talos-baremetal.sh upgrade-k8s               Roll Kubernetes upgrades
#
# Inputs (all version controlled, no secrets):
#   talos/nodes.yaml      machine inventory
#   talos/versions.yaml   pinned Talos + Kubernetes versions
#   talos/schematic.yaml  Image Factory extensions
#   talos/patches/        machine configuration patches
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TALOS_DIR="$REPO_ROOT/talos"
OUT_DIR="$TALOS_DIR/_out"
NODES_DIR="$OUT_DIR/nodes"
SECRETS_FILE="$OUT_DIR/secrets.yaml"
SECRETS_ENC="$TALOS_DIR/secrets.enc.yaml"
KUBECONFIG_PATH="$OUT_DIR/kubeconfig"
TALOSCONFIG_PATH="$OUT_DIR/talosconfig"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    local missing=()
    command -v talosctl >/dev/null 2>&1 || missing+=("talosctl")
    command -v kubectl >/dev/null 2>&1 || missing+=("kubectl")
    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    command -v curl >/dev/null 2>&1 || missing+=("curl")
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi
}

read_versions() {
    TALOS_VERSION="$(grep -E '^talos:' "$TALOS_DIR/versions.yaml" | awk '{print $2}')"
    K8S_VERSION="$(grep -E '^kubernetes:' "$TALOS_DIR/versions.yaml" | awk '{print $2}')"
    export TALOS_VERSION="v${TALOS_VERSION#v}"
    export K8S_VERSION="${K8S_VERSION#v}"
}

list_nodes() {
    local role="${1:-}" limit="${2:-}"
    python3 - "$TALOS_DIR/nodes.yaml" "$role" "$limit" <<'PYEOF'
import sys

path = sys.argv[1]
role = sys.argv[2] if len(sys.argv) > 2 else ""
limit = sys.argv[3] if len(sys.argv) > 3 else ""

current_role = ""
current = {}
order = []

def flush():
    if current and current.get("hostname"):
        order.append((current_role, dict(current)))

with open(path) as handle:
    for raw in handle:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in ("controlplanes:", "workers:"):
            flush()
            current_role = "controlplane" if stripped == "controlplanes:" else "worker"
            current = {}
            continue
        if stripped.startswith("- hostname:"):
            flush()
            current = {"hostname": stripped.split(":", 1)[1].strip()}
            continue
        if ":" in stripped and current_role:
            key, value = stripped.split(":", 1)
            current[key.strip()] = value.strip()

flush()

for node_role, node in order:
    if role and node_role != role:
        continue
    if limit and node.get("hostname") != limit:
        continue
    print(f"{node_role}\t{node.get('hostname', '')}\t{node.get('ip', '')}\t{node.get('installDisk', '')}")
PYEOF
}

read_inventory() {
    CLUSTER_NAME="$(grep -E '^clusterName:' "$TALOS_DIR/nodes.yaml" | awk '{print $2}')"
    ENDPOINT="$(grep -E '^controlPlaneEndpoint:' "$TALOS_DIR/nodes.yaml" | awk '{print $2}')"
    FIRST_CP_IP="$(list_nodes controlplane | head -n 1 | cut -f3)"
}

schematic_installer_image() {
    read_versions
    local schematic_id
    schematic_id="$(curl -sX POST --data-binary @"$TALOS_DIR/schematic.yaml" -H "Content-Type: application/yaml" https://factory.talos.dev/schematics | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
    echo "factory.talos.dev/installer/${schematic_id}:${TALOS_VERSION#v}"
}

cmd_iso_url() {
    read_versions
    local image="$1"
    local schematic_id="${image%%:*}"
    schematic_id="${schematic_id##*/}"
    local version="${image##*:}"
    log_info "Installer image: $image"
    log_info "Bootable ISO:    https://factory.talos.dev/image/${schematic_id}/${version}/metal-amd64.iso"
    log_info "ARM64 ISO:       https://factory.talos.dev/image/${schematic_id}/${version}/metal-arm64.iso"
}

resolve_secrets() {
    if [[ -n "${SOPS_AGE_KEY:-}" ]] && command -v sops >/dev/null 2>&1 && [[ -f "$SECRETS_ENC" ]]; then
        log_info "Decrypting committed secrets bundle..."
        mkdir -p "$OUT_DIR"
        sops --decrypt "$SECRETS_ENC" > "$SECRETS_FILE"
        return
    fi
    if [[ -f "$SECRETS_FILE" ]]; then
        log_info "Reusing local secrets bundle at $SECRETS_FILE"
        return
    fi
    return 1
}

cmd_gen_secrets() {
    mkdir -p "$OUT_DIR"
    if resolve_secrets 2>/dev/null; then
        log_success "Secrets already exist, nothing to do"
        return
    fi
    log_info "Generating cluster secrets (once per cluster)..."
    talosctl gen secrets -o "$SECRETS_FILE"
    if [[ -n "${SOPS_AGE_KEY:-}" ]] && command -v sops >/dev/null 2>&1; then
        log_info "Storing encrypted copy at $SECRETS_ENC"
        sops --encrypt --age "${SOPS_AGE_RECIPIENT:?set SOPS_AGE_RECIPIENT}" --output "$SECRETS_ENC" "$SECRETS_FILE"
    else
        log_warn "No SOPS setup detected; secrets live only in gitignored $SECRETS_FILE - back it up"
    fi
    log_success "Secrets ready"
}

cmd_gen_config() {
    check_prerequisites
    read_versions
    read_inventory
    cmd_gen_secrets
    local installer_image
    installer_image="$(schematic_installer_image)"
    log_info "Rendering machine configuration with installer $installer_image ..."
    mkdir -p "$OUT_DIR" "$NODES_DIR"
    talosctl gen config "$CLUSTER_NAME" "$ENDPOINT" \
        --with-secrets "$SECRETS_FILE" \
        --talos-version "$TALOS_VERSION" \
        --kubernetes-version "$K8S_VERSION" \
        --install-image "$installer_image" \
        --config-patch @"$TALOS_DIR/patches/common.yaml" \
        --config-patch-control-plane @"$TALOS_DIR/patches/controlplane.yaml" \
        --config-patch-worker @"$TALOS_DIR/patches/worker.yaml" \
        -o "$OUT_DIR"
    log_info "Splitting per-node configs (hostname + install disk)..."
    while IFS=$'\t' read -r role hostname ip disk; do
        [[ -z "$hostname" ]] && continue
        local src="$OUT_DIR/controlplane.yaml"
        [[ "$role" == "worker" ]] && src="$OUT_DIR/worker.yaml"
        HOSTNAME="$hostname" DISK="$disk" python3 - "$src" "$NODES_DIR/${hostname}.yaml" <<'PYEOF'
import re
import sys

src, dest = sys.argv[1], sys.argv[2]
import os
hostname = os.environ["HOSTNAME"]
disk = os.environ["DISK"]

with open(src) as handle:
    text = handle.read()

docs = re.split(r'(?m)^---\s*$', text)
out = []
for doc in docs:
    if "kind: HostnameConfig" in doc:
        updated, count = re.subn(r'(?m)^auto:.*$', f'hostname: {hostname}', doc, count=1)
        if count:
            doc = updated
        elif not re.search(r'(?m)^hostname:', doc):
            doc = doc.rstrip("\n") + f'\nhostname: {hostname}\n'
    if "kind: UnattendedInstallConfig" in doc and disk:
        doc = re.sub(r'match: disk\.dev_path == "[^"]*"', f'match: disk.dev_path == "{disk}"', doc)
    out.append(doc)

with open(dest, "w") as handle:
    handle.write("---\n".join(out))
PYEOF
    done < <(list_nodes)
    log_success "Per-node configs written to $NODES_DIR"
}

cmd_apply() {
    local role="" limit=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --role) role="$2"; shift 2 ;;
            --limit) limit="$2"; shift 2 ;;
            *) log_error "Unknown flag: $1"; exit 1 ;;
        esac
    done
    [[ -d "$NODES_DIR" ]] || cmd_gen_config
    while IFS=$'\t' read -r node_role hostname ip disk; do
        [[ -z "$hostname" ]] && continue
        log_info "Applying configuration to $hostname ($ip)..."
        talosctl apply-config --insecure --file "$NODES_DIR/${hostname}.yaml" --nodes "$ip"
    done < <(list_nodes "$role" "$limit")
    log_success "Configuration applied"
}

wait_for_maintenance() {
    read_inventory
    log_info "Waiting for machines to answer the Talos API..."
    while IFS=$'\t' read -r _ hostname ip _; do
        [[ -z "$hostname" ]] && continue
        until talosctl --talosconfig "$TALOSCONFIG_PATH" --nodes "$ip" version --insecure >/dev/null 2>&1; do
            sleep 5
        done
        log_info "$hostname is in maintenance mode"
    done < <(list_nodes)
}

cmd_bootstrap() {
    read_inventory
    log_info "Bootstrapping etcd on $FIRST_CP_IP ..."
    talosctl bootstrap --talosconfig "$TALOSCONFIG_PATH" --nodes "$FIRST_CP_IP"
    log_success "Bootstrap requested"
}

cmd_kubeconfig() {
    read_inventory
    log_info "Fetching kubeconfig..."
    talosctl kubeconfig "$KUBECONFIG_PATH" --talosconfig "$TALOSCONFIG_PATH" --nodes "$FIRST_CP_IP" --force
    log_info "Waiting for Kubernetes API..."
    until KUBECONFIG="$KUBECONFIG_PATH" kubectl get nodes >/dev/null 2>&1; do
        sleep 5
    done
    log_success "kubeconfig written to $KUBECONFIG_PATH"
    echo ""
    echo "To use: export KUBECONFIG=$KUBECONFIG_PATH"
}

cmd_argocd() {
    export KUBECONFIG="$KUBECONFIG_PATH"
    log_info "Installing ArgoCD..."
    kubectl apply -k "$REPO_ROOT/bootstrap/argocd"
    kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
    kubectl apply -f "$REPO_ROOT/bootstrap/root.yaml"
    log_success "GitOps bootstrap applied"
}

cmd_up() {
    check_prerequisites
    cmd_gen_config
    wait_for_maintenance
    cmd_apply
    cmd_bootstrap
    cmd_kubeconfig
    cmd_argocd
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
}

cmd_upgrade() {
    local kind="$1"
    read_versions
    read_inventory
    local image=""
    if [[ "$kind" == "talos" ]]; then
        image="$(schematic_installer_image)"
    fi
    stage_upgrade() {
        local scope="$1"
        while IFS=$'\t' read -r _ hostname ip _; do
            [[ -z "$hostname" ]] && continue
            log_info "Upgrading $kind on $hostname ..."
            if [[ "$kind" == "talos" ]]; then
                talosctl upgrade --talosconfig "$TALOSCONFIG_PATH" --nodes "$ip" --image "$image" --wait
            else
                talosctl upgrade-k8s --talosconfig "$TALOSCONFIG_PATH" --nodes "$ip" --to "$K8S_VERSION" --wait
            fi
        done < <(list_nodes "$scope")
    }
    stage_upgrade controlplane
    stage_upgrade worker
    log_success "$kind upgrade complete"
}

case "${1:-help}" in
    iso-url)
        check_prerequisites
        cmd_iso_url "$(schematic_installer_image)"
        ;;
    gen-secrets)
        check_prerequisites
        cmd_gen_secrets
        ;;
    gen-config)
        cmd_gen_config
        ;;
    apply)
        shift
        check_prerequisites
        read_inventory
        cmd_apply "$@"
        ;;
    bootstrap)
        check_prerequisites
        cmd_bootstrap
        ;;
    kubeconfig)
        check_prerequisites
        cmd_kubeconfig
        ;;
    up)
        cmd_up
        ;;
    upgrade-talos)
        check_prerequisites
        cmd_upgrade talos
        ;;
    upgrade-k8s)
        check_prerequisites
        cmd_upgrade k8s
        ;;
    *)
        echo "Usage: $0 {iso-url|up|gen-secrets|gen-config|apply|bootstrap|kubeconfig|upgrade-talos|upgrade-k8s}"
        exit 1
        ;;
esac

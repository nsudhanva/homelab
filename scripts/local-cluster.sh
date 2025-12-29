#!/usr/bin/env bash
#
# local-cluster.sh - One-command local Kubernetes cluster with Multipass
#
# Usage:
#   ./scripts/local-cluster.sh up      # Create and provision the cluster
#   ./scripts/local-cluster.sh down    # Destroy the cluster
#   ./scripts/local-cluster.sh status  # Show cluster status
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
KEY_PATH="$REPO_ROOT/ansible/.keys/multipass"
KUBECONFIG_PATH="/tmp/homelab-admin.conf"

# VM Configuration
CP_NAME="homelab-cp"
DEFAULT_WORKER_COUNT=2
WORKER_COUNT="${WORKER_COUNT:-$DEFAULT_WORKER_COUNT}"
WORKER_NAMES=()
if [[ "$WORKER_COUNT" -gt 0 ]]; then
    for i in $(seq 1 "$WORKER_COUNT"); do
        WORKER_NAMES+=("homelab-w${i}")
    done
fi
ALL_VMS=("$CP_NAME")
if [[ ${#WORKER_NAMES[@]} -gt 0 ]]; then
    ALL_VMS+=("${WORKER_NAMES[@]}")
fi

# Resource settings
VM_CPUS="${VM_CPUS:-2}"
VM_MEMORY="${VM_MEMORY:-4G}"
VM_DISK="${VM_DISK:-20G}"
CILIUM_HUBBLE_ENABLED="${CILIUM_HUBBLE_ENABLED:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    log_info "Checking prerequisites..."
    local missing=()

    command -v multipass >/dev/null 2>&1 || missing+=("multipass")
    command -v ansible-playbook >/dev/null 2>&1 || missing+=("ansible")
    command -v kubectl >/dev/null 2>&1 || missing+=("kubectl")

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing[*]}"
        echo ""
        echo "Install on macOS:"
        echo "  brew install --cask multipass"
        echo "  brew install ansible kubectl"
        echo ""
        echo "Install on Ubuntu:"
        echo "  sudo snap install multipass"
        echo "  sudo apt-get install -y ansible"
        echo "  sudo snap install kubectl --classic"
        exit 1
    fi

    log_success "All prerequisites installed"
}

create_ssh_key() {
    if [[ -f "$KEY_PATH" ]]; then
        log_info "SSH key already exists at $KEY_PATH"
        return
    fi
    log_info "Creating SSH key for VMs..."
    mkdir -p "$(dirname "$KEY_PATH")"
    ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -q
    log_success "SSH key created"
}

create_vms() {
    log_info "Launching Multipass VMs..."

    for vm in "${ALL_VMS[@]}"; do
        if multipass info "$vm" &>/dev/null; then
            log_info "VM $vm already exists, skipping..."
            continue
        fi

        log_info "Creating $vm..."
        multipass launch --name "$vm" --cpus "$VM_CPUS" --memory "$VM_MEMORY" --disk "$VM_DISK" 24.04

        # Wait for VM to be ready
        sleep 5
    done

    log_success "All VMs created"
}

inject_ssh_keys() {
    log_info "Injecting SSH keys into VMs..."
    for vm in "${ALL_VMS[@]}"; do
        multipass exec "$vm" -- bash -c "mkdir -p /home/ubuntu/.ssh && chmod 700 /home/ubuntu/.ssh"
        cat "$KEY_PATH.pub" | multipass exec "$vm" -- bash -c "cat >> /home/ubuntu/.ssh/authorized_keys && chmod 600 /home/ubuntu/.ssh/authorized_keys"
    done
    log_success "SSH keys injected"
}

get_vm_ip() {
    local vm=$1
    multipass info "$vm" --format json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['$vm']['ipv4'][0])"
}

generate_inventory() {
    log_info "Generating Ansible inventory..."

    local cp_ip
    cp_ip=$(get_vm_ip "$CP_NAME")

    local inv_file="$REPO_ROOT/ansible/inventory/local-cluster.yaml"
    cat > "$inv_file" << EOF
all:
  vars:
    ansible_user: ubuntu
    ansible_ssh_private_key_file: ${KEY_PATH}
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no'
  children:
    k8s_nodes:
      children:
        control_plane:
          hosts:
            ${CP_NAME}:
              ansible_host: ${cp_ip}
        workers:
          hosts:
EOF

    if [[ "$WORKER_COUNT" -gt 0 ]]; then
        for worker in "${WORKER_NAMES[@]}"; do
            local worker_ip
            worker_ip=$(get_vm_ip "$worker")
            cat >> "$inv_file" << EOF
            ${worker}:
              ansible_host: ${worker_ip}
EOF
        done
    fi

    log_success "Inventory written to $inv_file"
}

run_ansible() {
    log_info "Running Ansible provisioning (this may take a few minutes)..."

    cd "$REPO_ROOT"
    ANSIBLE_HOST_KEY_CHECKING=False \
    ANSIBLE_ROLES_PATH=ansible/roles \
    ansible-playbook -i ansible/inventory/local-cluster.yaml \
        ansible/playbooks/provision-cpu.yaml \
        -e @ansible/group_vars/all.yaml

    log_success "Ansible provisioning complete"
}

init_control_plane() {
    log_info "Initializing Kubernetes control plane..."

    multipass exec "$CP_NAME" -- sudo kubeadm init \
        --pod-network-cidr=10.244.0.0/16 \
        --skip-phases=addon/kube-proxy

    if [[ "$WORKER_COUNT" -eq 0 ]]; then
        multipass exec "$CP_NAME" -- sudo kubectl --kubeconfig /etc/kubernetes/admin.conf \
            taint nodes --all node-role.kubernetes.io/control-plane- || true
    fi

    log_success "Control plane initialized"
}

join_workers() {
    if [[ "$WORKER_COUNT" -eq 0 ]]; then
        log_info "No worker nodes requested, skipping join..."
        return
    fi

    log_info "Joining worker nodes..."

    local join_cmd
    join_cmd=$(multipass exec "$CP_NAME" -- sudo kubeadm token create --print-join-command)

    for worker in "${WORKER_NAMES[@]}"; do
        log_info "Joining $worker..."
        multipass exec "$worker" -- sudo bash -c "$join_cmd"
    done

    log_success "All workers joined"
}

copy_kubeconfig() {
    log_info "Copying kubeconfig to $KUBECONFIG_PATH..."

    multipass exec "$CP_NAME" -- sudo cp /etc/kubernetes/admin.conf /home/ubuntu/admin.conf
    multipass exec "$CP_NAME" -- sudo chown ubuntu:ubuntu /home/ubuntu/admin.conf
    multipass transfer "$CP_NAME":/home/ubuntu/admin.conf "$KUBECONFIG_PATH"

    # Update server IP to use VM's actual IP
    local cp_ip
    cp_ip=$(get_vm_ip "$CP_NAME")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|server: https://.*:6443|server: https://${cp_ip}:6443|g" "$KUBECONFIG_PATH"
    else
        sed -i "s|server: https://.*:6443|server: https://${cp_ip}:6443|g" "$KUBECONFIG_PATH"
    fi

    log_success "Kubeconfig saved to $KUBECONFIG_PATH"
    echo ""
    echo "To use: export KUBECONFIG=$KUBECONFIG_PATH"
}

install_cilium() {
    log_info "Installing Cilium CNI..."

    local cilium_version
    cilium_version=$(grep -E "cilium_version:" "$REPO_ROOT/ansible/group_vars/all.yaml" | head -n 1 | awk -F'"' '{print $2}')

    # Install Cilium CLI inside the VM
    multipass exec "$CP_NAME" -- bash -c '
        CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
        ARCH=$(uname -m)
        if [ "${ARCH}" = "aarch64" ]; then CILIUM_ARCH=arm64; else CILIUM_ARCH=amd64; fi
        curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CILIUM_ARCH}.tar.gz{,.sha256sum}
        sha256sum --check cilium-linux-${CILIUM_ARCH}.tar.gz.sha256sum
        sudo tar xzvfC cilium-linux-${CILIUM_ARCH}.tar.gz /usr/local/bin
        rm cilium-linux-${CILIUM_ARCH}.tar.gz cilium-linux-${CILIUM_ARCH}.tar.gz.sha256sum
    '

    # Install Cilium with required settings for Tailscale compatibility
    local cp_ip
    cp_ip=$(get_vm_ip "$CP_NAME")
    local extra_args=()
    if [[ "$CILIUM_HUBBLE_ENABLED" != "true" ]]; then
        extra_args+=(--set hubble.relay.enabled=false)
        extra_args+=(--set hubble.ui.enabled=false)
    fi
    multipass transfer "$REPO_ROOT/infrastructure/cilium/values.cilium" "$CP_NAME":/home/ubuntu/cilium-values.yaml
    multipass exec "$CP_NAME" -- sudo cilium install \
        --kubeconfig /etc/kubernetes/admin.conf \
        --version "$cilium_version" \
        --values /home/ubuntu/cilium-values.yaml \
        --set k8sServiceHost="$cp_ip" \
        "${extra_args[@]}"

    # Wait for Cilium to be ready
    log_info "Waiting for Cilium to be ready..."
    multipass exec "$CP_NAME" -- sudo cilium status --kubeconfig /etc/kubernetes/admin.conf --wait

    log_success "Cilium installed"
}

wait_for_nodes() {
    log_info "Waiting for all nodes to be Ready..."
    local max_attempts=60
    local attempt=0
    local expected_nodes=${#ALL_VMS[@]}

    while [[ $attempt -lt $max_attempts ]]; do
        local total_nodes
        local ready_nodes

        # Capture output safely, ignoring errors during capture to prevent script exit
        local node_output
        if node_output=$(kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes --no-headers 2>/dev/null); then
            total_nodes=$(echo "$node_output" | wc -l | tr -d ' ')
            ready_nodes=$(echo "$node_output" | grep " Ready" | wc -l | tr -d ' ')
        else
            total_nodes=0
            ready_nodes=0
        fi

        if [[ "$total_nodes" -ge "$expected_nodes" && "$ready_nodes" -eq "$total_nodes" ]]; then
            log_success "All $total_nodes nodes are Ready"
            return 0
        fi

        log_info "Nodes: $ready_nodes/$expected_nodes Ready. Waiting..."
        attempt=$((attempt + 1))
        sleep 10
    done

    log_error "Timed out waiting for nodes to be Ready"
    kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes
    return 1
}

run_smoke_test() {
    log_info "Running smoke test..."

    kubectl --kubeconfig "$KUBECONFIG_PATH" apply -f "$REPO_ROOT/ansible/tests/local-cluster/test-nginx/deployment.yaml"
    kubectl --kubeconfig "$KUBECONFIG_PATH" apply -f "$REPO_ROOT/ansible/tests/local-cluster/test-nginx/service.yaml"

    log_info "Waiting for test-nginx pod..."
    kubectl --kubeconfig "$KUBECONFIG_PATH" wait --for=condition=ready pod -l app=test-nginx --timeout=120s

    log_success "Smoke test passed!"
    echo ""
    kubectl --kubeconfig "$KUBECONFIG_PATH" get pods -l app=test-nginx -o wide
}

cluster_up() {
    echo ""
    echo "=========================================="
    echo "   Homelab Local Cluster Setup"
    echo "=========================================="
    echo ""

    check_prerequisites
    create_ssh_key
    create_vms
    inject_ssh_keys
    generate_inventory
    run_ansible
    init_control_plane
    join_workers
    copy_kubeconfig
    install_cilium
    wait_for_nodes
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
    echo "To destroy: ./scripts/local-cluster.sh down"
    echo ""
}

cluster_down() {
    log_info "Destroying local cluster..."

    for vm in "${ALL_VMS[@]}"; do
        if multipass info "$vm" &>/dev/null; then
            log_info "Deleting $vm..."
            multipass delete "$vm"
        fi
    done

    multipass purge
    rm -f "$KUBECONFIG_PATH"

    log_success "Cluster destroyed"
}

cluster_status() {
    echo ""
    echo "VM Status:"
    multipass list | grep -E "homelab|Name"
    echo ""

    if [[ -f "$KUBECONFIG_PATH" ]]; then
        echo "Kubernetes Status:"
        kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes -o wide 2>/dev/null || echo "  Cannot connect to cluster"
        echo ""
    else
        echo "No kubeconfig found at $KUBECONFIG_PATH"
    fi
}

# Main
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
        echo ""
        echo "Commands:"
        echo "  up      Create and provision the local cluster"
        echo "  down    Destroy the cluster and clean up"
        echo "  status  Show cluster status"
        exit 1
        ;;
esac

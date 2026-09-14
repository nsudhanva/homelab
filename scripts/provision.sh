#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
KUBECONFIG_PATH="$REPO_ROOT/k3s.kubeconfig"

cd "$REPO_ROOT"

echo "=========================================="
echo "   Provisioning Homelab K3s Cluster       "
echo "=========================================="

ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml "$@"

echo ""
echo "=========================================="
echo "   Cluster Provisioned Successfully!      "
echo "=========================================="
echo ""
echo "KUBECONFIG: $KUBECONFIG_PATH"
echo ""
echo "To interact with your cluster:"
echo "  export KUBECONFIG=$KUBECONFIG_PATH"
echo "  kubectl get nodes -o wide"
echo "  kubectl get pods -A"
echo ""

export KUBECONFIG="$KUBECONFIG_PATH"
kubectl get nodes -o wide

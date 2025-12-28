---
sidebar_position: 7
title: Local Multipass Cluster
---

# Local Multipass Cluster

This tutorial runs a multi-node Kubernetes cluster on local VMs using Multipass. It is intended as an optional rehearsal path before the bare-metal setup, and mirrors the same control plane and worker layout.

## Quick Start (Automated)

Use the automation script for a one-command setup:

```bash
./scripts/local-cluster.sh up
```

This handles everything: VM creation, Ansible provisioning, kubeadm initialization, Cilium installation, and smoke testing.

When done:

```bash
./scripts/local-cluster.sh down
```

---

## Manual Setup (Step by Step)

If you prefer to understand each step or need to customize the process, follow the manual instructions below.

### Prerequisites

- Multipass installed on your workstation
- Ansible installed on your workstation
- kubectl installed on your workstation
- At least 12GB of free RAM

### Step 1: Install host tools

macOS (Homebrew):

```bash
brew install --cask multipass
brew install ansible kubectl
```

Ubuntu 24.04 (Snap + APT):

```bash
sudo snap install multipass
sudo apt-get update && sudo apt-get install -y ansible
sudo snap install kubectl --classic
```

### Step 2: Create a dedicated SSH key

```bash
mkdir -p ansible/.keys
ssh-keygen -t ed25519 -f ansible/.keys/multipass -N ""
```

### Step 3: Launch the VMs

```bash
multipass launch --name homelab-cp --cpus 2 --memory 4G --disk 20G 24.04
multipass launch --name homelab-w1 --cpus 2 --memory 4G --disk 20G 24.04
multipass launch --name homelab-w2 --cpus 2 --memory 4G --disk 20G 24.04
```

### Step 4: Add the SSH key to each VM

```bash
for node in homelab-cp homelab-w1 homelab-w2; do
  multipass exec "$node" -- bash -c "mkdir -p /home/ubuntu/.ssh && cat >> /home/ubuntu/.ssh/authorized_keys" < ansible/.keys/multipass.pub
done
```

### Step 5: Generate the Ansible inventory

Get the VM IPs and create the inventory:

```bash
multipass list
```

Create `ansible/inventory/local-cluster.yaml` with the IPs from the output.

### Step 6: Run Ansible provisioning

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=ansible/roles \
ansible-playbook -i ansible/inventory/local-cluster.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml
```

### Step 7: Initialize the control plane

```bash
multipass exec homelab-cp -- sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

### Step 8: Join the workers

```bash
JOIN_CMD=$(multipass exec homelab-cp -- sudo kubeadm token create --print-join-command)
multipass exec homelab-w1 -- sudo bash -c "$JOIN_CMD"
multipass exec homelab-w2 -- sudo bash -c "$JOIN_CMD"
```

### Step 9: Copy kubeconfig to your workstation

```bash
multipass exec homelab-cp -- sudo cp /etc/kubernetes/admin.conf /home/ubuntu/admin.conf
multipass exec homelab-cp -- sudo chown ubuntu:ubuntu /home/ubuntu/admin.conf
multipass transfer homelab-cp:/home/ubuntu/admin.conf /tmp/homelab-admin.conf
export KUBECONFIG=/tmp/homelab-admin.conf
```

### Step 10: Install Cilium

Install the Cilium CLI inside the control plane VM:

```bash
multipass exec homelab-cp -- bash -c '
  CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
  ARCH=$(uname -m)
  if [ "${ARCH}" = "aarch64" ]; then CILIUM_ARCH=arm64; else CILIUM_ARCH=amd64; fi
  curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CILIUM_ARCH}.tar.gz{,.sha256sum}
  sha256sum --check cilium-linux-${CILIUM_ARCH}.tar.gz.sha256sum
  sudo tar xzvfC cilium-linux-${CILIUM_ARCH}.tar.gz /usr/local/bin
  rm cilium-linux-${CILIUM_ARCH}.tar.gz*
'
```

Get the Cilium version and install:

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | awk -F'"' '{print $2}')
multipass exec homelab-cp -- sudo cilium install \
  --kubeconfig /etc/kubernetes/admin.conf \
  --version $CILIUM_VERSION \
  --set kubeProxyReplacement=true \
  --set socketLB.hostNamespaceOnly=true
```

:::warning

The `socketLB.hostNamespaceOnly=true` setting is required for Tailscale Operator LoadBalancer services to work correctly. See [Cilium CNI](./cilium.md) for details.

:::

Wait for Cilium to be ready:

```bash
multipass exec homelab-cp -- sudo cilium status --kubeconfig /etc/kubernetes/admin.conf --wait
```

### Step 11: Verify the cluster

```bash
kubectl get nodes -o wide
kubectl apply -f ansible/tests/local-cluster/test-nginx/deployment.yaml
kubectl apply -f ansible/tests/local-cluster/test-nginx/service.yaml
kubectl get pods -l app=test-nginx
```

### Step 12: Tear down

```bash
multipass delete homelab-cp homelab-w1 homelab-w2
multipass purge
```

---

## Next Steps

When ready for real hardware:

- [Prerequisites](./prerequisites.md) - Hardware and network requirements
- [System Preparation](./system-prep.md) - OS configuration
- [Kubernetes](./kubernetes.md) - Cluster initialization

The Ansible roles and GitOps layout are identical; only the inventory changes.

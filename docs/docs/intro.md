---
sidebar_position: 1
title: Home
---

# Homelab

Multi-node bare-metal Kubernetes cluster on Ubuntu 24.04 LTS, managed via GitOps with ArgoCD.

## Quick Start

Choose your path based on where you want to run Kubernetes:

### Option A: Local Rehearsal (Recommended First)

Run a full multi-node cluster on your workstation using Multipass VMs. This mirrors the bare-metal setup without needing real hardware.

**One command:**

```bash
./scripts/local-cluster.sh up
```

This script:

- Creates 3 VMs (1 control plane, 2 workers)
- Runs Ansible provisioning
- Initializes Kubernetes with kubeadm
- Installs Cilium CNI
- Runs a smoke test

**Time:** ~10 minutes

**Prerequisites:** Multipass, Ansible, kubectl ([Install guide](./tutorials/local-multipass-cluster.md#step-1-install-host-tools))

When done, destroy with:

```bash
./scripts/local-cluster.sh down
```

---

### Option B: Bare Metal Deployment

Deploy to real Ubuntu 24.04 hardware with SSH access.

**Three commands:**

```bash
# 1. Edit inventory with your IPs
nano ansible/inventory/hosts.yaml

# 2. Provision all nodes
ansible-playbook -i ansible/inventory/hosts.yaml ansible/playbooks/provision-cpu.yaml

# 3. Initialize control plane and install CNI (run on control plane node)
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
cilium install --set kubeProxyReplacement=true --set socketLB.hostNamespaceOnly=true
```

Then bootstrap GitOps:

```bash
kubectl apply -f bootstrap/root.yaml
```

ArgoCD will sync all infrastructure and apps from Git automatically.

**Detailed guide:** [Prerequisites](./tutorials/prerequisites.md) → [System Prep](./tutorials/system-prep.md) → [Kubernetes](./tutorials/kubernetes.md)

---

## What Gets Deployed

Once ArgoCD syncs, you get:

| Component | Purpose |
|-----------|---------|
| **Cilium** | CNI with kube-proxy replacement |
| **ArgoCD** | GitOps continuous deployment |
| **Longhorn** | Distributed block storage |
| **Envoy Gateway** | Gateway API ingress controller |
| **Tailscale Operator** | VPN-based LoadBalancer |
| **cert-manager** | Automatic TLS certificates |
| **ExternalDNS** | Automatic DNS record management |

## Repository Structure

```
homelab/
├── ansible/              # Node provisioning (Ansible)
│   ├── inventory/        # Host definitions
│   ├── playbooks/        # Playbook entrypoints
│   └── roles/            # Reusable roles
├── bootstrap/            # ArgoCD bootstrap
├── infrastructure/       # Cluster components (ArgoCD manages)
├── apps/                 # User workloads (ArgoCD manages)
├── scripts/              # Automation scripts
└── docs/                 # This documentation
```

## Automation Model

Everything flows through two systems:

- **Ansible** provisions nodes (OS, container runtime, kubelet)
- **ArgoCD** applies cluster state from Git (helm charts, manifests)

Manual `kubectl apply` is discouraged. Push to Git and let ArgoCD reconcile.

Read more: [Automation Model](./explanation/automation-model.md)

## Day-2 Operations

After initial setup:

- [Deploy Apps With GitOps](./how-to/deploy-apps.md) - Add your own workloads
- [Tailscale Custom Domains](./how-to/tailscale.md) - Expose apps via HTTPS
- [Maintenance](./how-to/maintenance.md) - Upgrades and routine checks

## Deep Dives

- [Gateway API and Networking](./explanation/gateway-networking.md) - How traffic flows through Tailscale → Envoy → Apps
- [Local vs Bare Metal](./explanation/local-vs-baremetal.md) - Differences between Multipass and real hardware

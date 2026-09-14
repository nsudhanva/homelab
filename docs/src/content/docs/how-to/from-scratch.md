---
title: Build K3s Cluster from Scratch
description: Complete guide to provisioning a bare-metal Kubernetes cluster on Ubuntu 26.04 using K3s, automated Ansible provisioning, ArgoCD GitOps, and Vault secrets management.
keywords:
  - k3s from scratch
  - build kubernetes cluster
  - k3s cluster setup
  - ansible k3s automation
  - argocd gitops bootstrap
  - kubernetes homelab
sidebar:
  order: 1
---

# From Scratch

Use this guide to provision a bare-metal Kubernetes cluster on Ubuntu 26.04 using Ansible and K3s with this repo as the single source of truth. One command takes a machine from base OS to a running GitOps-managed cluster.

## Step 1: Configure Inventory

Review the host target in `ansible/inventory/hosts.yaml` and cluster settings in `ansible/group_vars/all.yaml`. Ensure SSH access and sudo privileges are active on the target machine.

```yaml
all:
  children:
    k3s_cluster:
      children:
        k3s_servers:
          hosts:
            legion:
              ansible_host: 100.66.139.118
              ansible_user: sudhanva
              ansible_ssh_common_args: "-o StrictHostKeyChecking=accept-new"
              k3s_node_ip: "10.0.0.133"
              k3s_external_ip: "100.66.139.118"
```

## Step 2: Run Automated Provisioning

Run the automated provisioning script from the repository root:

```bash
./scripts/provision.sh
```

The script executes the Ansible playbook `ansible/site.yaml` which handles:

- Host prerequisites: Kernel modules (`overlay`, `br_netfilter`), sysctls, and storage path creation on the dedicated SSD (`/home/k3s-storage`).
- NVIDIA integration: Installs NVIDIA Container Toolkit, generates CDI specifications, and configures containerd GPU runtime.
- K3s Server: Installs K3s, disables Traefik and ServiceLB, attaches to Tailscale and LAN IPs, and starts the systemd service.
- Kubeconfig: Fetches the cluster credentials and configures the Tailscale endpoint.
- GitOps bootstrap: Deploys ArgoCD with server-side apply and applies the root Application (`bootstrap/root.yaml`).

## Step 3: Validate the Cluster

Confirm the node is ready and pods are running:

```bash
export KUBECONFIG="./k3s.kubeconfig"
kubectl get nodes -o wide
kubectl get pods -A
kubectl get apps -n argocd
```

## Step 4: Configure Vault and External Secrets

Follow [Vault](../how-to/vault.md) to initialize Vault and sync the required secrets for ExternalDNS, cert-manager, and the Tailscale operator.

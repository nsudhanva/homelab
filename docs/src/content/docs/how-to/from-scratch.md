---
title: Build K3s Cluster from Scratch
description: Provision a bare-metal Kubernetes cluster on Ubuntu 26.04 with K3s, automated Ansible provisioning, ArgoCD GitOps, and Vault secrets management.
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

Use this guide to provision a bare-metal Kubernetes cluster on Ubuntu 26.04 with Ansible and K3s. This repo is the single source of truth. One command changes a machine from a base OS to a running cluster that GitOps manages.

## Step 1: Configure Inventory

Examine the target host in `ansible/inventory/hosts.yaml` and the cluster settings in `ansible/group_vars/all.yaml`. Make sure that you have SSH access and sudo privileges on the target machine.

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
              k3s_node_ip: "100.66.139.118"
              k3s_external_ip: "100.66.139.118"
```

## Step 2: Run Automated Provisioning

Run the automated provisioning script from the repository root.

```bash
./scripts/provision.sh
```

The script runs the Ansible playbook `ansible/site.yaml`. The playbook does these tasks:

- Host prerequisites: It loads the kernel modules (`overlay`, `br_netfilter`), sets the sysctls, and creates the storage path on the dedicated SSD (`/home/k3s-storage`).
- NVIDIA integration: It installs the NVIDIA Container Toolkit, generates the CDI specifications, and configures the containerd GPU runtime.
- Tailscale: It makes sure that Tailscale runs. It disables Tailscale DNS on the node, so the host uses its upstream network resolvers.
- K3s Server: It installs K3s and disables Traefik and ServiceLB. It uses the Tailscale IP as the node IP and reserves CPU and memory for the system. It sets K3s to start after `tailscaled`, then starts the systemd service.
- Kubeconfig: It gets the cluster credentials and configures the Tailscale endpoint.
- GitOps bootstrap: It deploys ArgoCD with server-side apply and applies the root Application (`bootstrap/root.yaml`).

## Step 3: Validate the Cluster

Make sure that the node is ready and that the pods run.

```bash
export KUBECONFIG="./k3s.kubeconfig"
kubectl get nodes -o wide
kubectl get pods -A
kubectl get apps -n argocd
```

## Step 4: Configure Vault and External Secrets

Follow [Vault](../how-to/vault.md) to initialize Vault. Then sync the necessary secrets for ExternalDNS, cert-manager, and the Tailscale operator.

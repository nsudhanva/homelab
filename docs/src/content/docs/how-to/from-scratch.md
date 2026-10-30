---
title: Build K3s Cluster from Scratch
description: Provision a bare-metal K3s cluster on Ubuntu 26.04 with Ansible, then bootstrap ArgoCD and configure Vault.
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

Use this guide to provision a bare-metal Kubernetes cluster on Ubuntu 26.04 with Ansible and K3s. This repository is the single source of truth. One command changes a machine with a base OS into a running cluster that ArgoCD manages.

## Step 1: Configure the Inventory

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

## Step 2: Run the Provisioning Script

Run the provisioning script from the repository root:

```bash
./scripts/provision.sh
```

The script runs the Ansible playbook `ansible/site.yaml`. The playbook runs these roles and tasks:

- Host prerequisites (`common`): The role installs the base packages and loads the kernel modules (`overlay`, `br_netfilter`). It sets the sysctls and creates the storage path on the dedicated SSD (`/home/k3s-storage`).
- NVIDIA integration (`nvidia`): The role makes sure that `nvidia-smi` runs and installs the NVIDIA Container Toolkit and `runc`. It generates the CDI specification at `/etc/cdi/nvidia.yaml`.
- Tailscale (`tailscale`): The role fails if Tailscale is not installed. It disables Tailscale DNS on the node, so the host uses its upstream network resolvers. It waits until `tailscale0` has the node IP.
- K3s server (`k3s_server`): The role writes `/etc/rancher/k3s/config.yaml`. This file disables Traefik, ServiceLB, and the bundled metrics-server, and sets `default-runtime: nvidia`. It also sets the Tailscale IP as the node IP and reserves CPU and memory for the system. The role starts K3s after `tailscaled`. If the `k3s` binary is not on the host, the role installs K3s `v1.37.1+k3s1`. Then it starts the systemd service.
- Kubeconfig: The playbook gets the cluster credentials and sets the Tailscale endpoint in the kubeconfig.
- GitOps bootstrap (`argocd`): The role deploys ArgoCD with server-side apply and applies the root Application (`bootstrap/root.yaml`).

## Step 3: Validate the Cluster

Make sure that the node is `Ready` and that the pods run:

```bash
export KUBECONFIG="./k3s.kubeconfig"
kubectl get nodes -o wide
kubectl get pods -A
kubectl get apps -n argocd
```

## Step 4: Configure Vault and External Secrets

Follow [Vault](/how-to/vault/) to initialize and unseal Vault, enable KV v2 at `kv/`, and configure the Kubernetes auth role for External Secrets. Then write the secrets that the ExternalSecrets read. Write the secrets for ExternalDNS, cert-manager, the Tailscale operator, and the ArgoCD repository first. The components that need these secrets stay degraded until Vault has the values.

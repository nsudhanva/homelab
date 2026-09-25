---
title: Ansible Inventory and Configuration
description: Configure Ansible inventory, group variables, and role settings to prepare the automated K3s provisioning pipeline.
keywords:
  - ansible configuration
  - k3s inventory
  - infrastructure as code
  - ansible roles k3s
  - bare metal automation
sidebar:
  order: 4
---

# Ansible Configuration

Every bare-metal node in this homelab is configured through version-controlled Ansible playbooks. Nothing is typed into a node by hand.

## Step 1: Learn the repository layout

The automation structure in `ansible/` manages the bare-metal lifecycle:

- `ansible/inventory/hosts.yaml`: Lists control plane nodes and worker nodes with hostnames, SSH users, and IP addresses.
- `ansible/group_vars/all.yaml`: Defines global cluster variables including pinned K3s versions, TLS SANs, and storage paths.
- `ansible/site.yaml`: The master playbook defining the sequence of roles applied to hosts.
- `ansible/roles/`: Modular tasks for OS preparation (`common`), Tailscale node settings (`tailscale`), GPU setup (`nvidia`), K3s server (`k3s_server`), and ArgoCD bootstrap (`argocd`). Each role has a matching tag in `ansible/site.yaml`, so you can run one role with `--tags`.

## Step 2: Configure host inventory

Inspect and update `ansible/inventory/hosts.yaml` with your node information:

```yaml
k3s_cluster:
  children:
    k3s_servers:
      hosts:
        legion:
          ansible_host: 100.66.139.118
          ansible_user: sudhanva
          k3s_node_ip: "100.66.139.118"
          k3s_external_ip: "100.66.139.118"
```

## Step 3: Configure cluster variables

Review `ansible/group_vars/all.yaml` to ensure cluster parameters match your network and storage layout:

```yaml
k3s_version: "v1.36.4+k3s1"
local_storage_path: "/home/k3s-storage"
tls_sans:
  - "100.66.139.118"
  - "10.0.0.133"
  - "legion"
  - "legion.ainu-herring.ts.net"
k3s_kubelet_args:
  - "kube-reserved=cpu=250m,memory=512Mi"
  - "system-reserved=cpu=250m,memory=512Mi"
  - "eviction-hard=memory.available<500Mi,nodefs.available<10%,imagefs.available<10%"
```

`k3s_node_ip` and `k3s_external_ip` are both the node's Tailscale IP. The Tailscale IP stays the same across LAN, DHCP, and interface changes (Ethernet or Wi-Fi), so the API server, kubelet, and host-network pods always have a reachable address. `k3s_kubelet_args` reserves CPU and memory for K3s and the OS so workloads cannot starve the control plane. See [Node Networking and DNS](../explanation/node-networking.md).

## Step 4: Verify Ansible connectivity

Test connectivity from your workstation to the target node:

```bash
ansible all -i ansible/inventory/hosts.yaml -m ping
```

If the ping reports `SUCCESS`, your automation environment is ready. Proceed to [K3s Bootstrap](./kubernetes.md) to execute the provisioning playbook.

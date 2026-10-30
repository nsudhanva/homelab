---
title: Ansible Inventory and Configuration
description: Configure the Ansible inventory, group variables, and role settings for the automatic K3s provisioning pipeline.
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

Ansible playbooks in version control configure each bare-metal node in this homelab. No person types commands into a node manually.

## Step 1: Learn the repository layout

The automation in `ansible/` manages the bare-metal lifecycle:

- `ansible/inventory/hosts.yaml`: Lists the nodes with their hostnames, SSH users, and IP addresses. It has one group, `k3s_servers`, under `k3s_cluster`. The only host is `legion`. There is no worker (agent) group.
- `ansible/group_vars/all.yaml`: Defines the global cluster variables. These include the K3s version, the TLS SANs, the storage path, and the local kubeconfig path.
- `ansible/site.yaml`: The main playbook. It applies the roles to the `k3s_servers` group in this order: `common`, `tailscale`, `nvidia`, `k3s_server`, `argocd`.
- `ansible/roles/`: Tasks for OS preparation (`common`), Tailscale node settings (`tailscale`), GPU setup (`nvidia`), K3s server (`k3s_server`), and ArgoCD bootstrap (`argocd`). Each role has a tag in `ansible/site.yaml`: `common`, `tailscale`, `nvidia`, `k3s`, and `argocd`. Note that the `k3s_server` role uses the tag `k3s`. Run one role with `--tags`.

## Step 2: Configure host inventory

Examine `ansible/inventory/hosts.yaml` and add the data for your nodes:

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

## Step 3: Configure cluster variables

Examine `ansible/group_vars/all.yaml`. Make sure that the cluster parameters agree with your network and storage layout:

```yaml
k3s_version: "v1.37.1+k3s1"
local_storage_path: "/home/k3s-storage"
kubeconfig_local_dest: "{{ playbook_dir }}/../k3s.kubeconfig"
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

`k3s_node_ip` and `k3s_external_ip` are both the Tailscale IP of the node. The Tailscale IP does not change when the LAN, the DHCP lease, or the interface (Ethernet or Wi-Fi) changes. Thus, the API server, the kubelet, and host-network pods always have an address that they can reach. `kubeconfig_local_dest` is where the playbook writes the cluster kubeconfig on your workstation (`k3s.kubeconfig` in the repo root). `k3s_version` is the version that the playbook installs when K3s is not on the host yet. The System Upgrade Controller does later upgrades. `k3s_kubelet_args` keeps CPU and memory for K3s and the OS, so workloads cannot take all resources from the control plane. Refer to [Node Networking and DNS](/explanation/node-networking/).

## Step 4: Verify Ansible connectivity

Test the connection from your workstation to the target node:

```bash
ansible all -i ansible/inventory/hosts.yaml -m ping
```

If the ping shows `SUCCESS`, your automation environment is ready. Go to [K3s Bootstrap](/tutorials/kubernetes/) and run the provisioning playbook.

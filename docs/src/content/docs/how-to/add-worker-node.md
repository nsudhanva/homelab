---
title: Add Worker Node to K3s Cluster
description: The scope of worker nodes in this K3s cluster. The cluster has one server node, and the repository has no automation to join a worker node.
keywords:
  - add k3s worker node
  - k3s cluster scaling
  - bare metal worker node
  - ansible k3s agent
  - kubernetes node expansion
sidebar:
  order: 2
---

The cluster has one server node, `legion`, and no worker nodes. The repository has no `k3s_agents` inventory group and no agent role, so it cannot join a worker node.

## Current Scope

These facts apply to the Ansible automation in `ansible/`:

- `ansible/site.yaml` targets only the `k3s_servers` group in `ansible/inventory/hosts.yaml`. If you run it with `--limit` on a new host, the host does not join the cluster.
- The `k3s_server` role installs K3s in server mode. It sets `node-ip` and `node-external-ip` to the Tailscale IP of the node (`k3s_node_ip` and `k3s_external_ip`).
- `ansible/roles/k3s_server/templates/config.yaml.j2` sets the node labels `gpu.nvidia.com/present=true` and `node.homelab/role=controlplane` for each server node. There is no per-node label variable.
- The `nvidia` role fails on each host where `nvidia-smi` does not run.

To provision the server node, see [From Scratch](/how-to/from-scratch/).

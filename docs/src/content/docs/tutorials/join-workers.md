---
title: Add Worker Nodes to K3s Cluster
description: The current state of worker nodes in this K3s homelab. The cluster has one server node, and the repo does not automate worker joins yet.
keywords:
  - k3s worker node
  - add node to cluster
  - ansible k3s agent
  - kubernetes cluster expansion
  - multi-node k3s
sidebar:
  order: 8
---

# Add Workers

:::caution

This repository does not automate worker joins yet. The steps on this page describe what exists today and what you must add first. Do not run the playbook against a new host and expect it to join as a worker.

:::

## What exists today

The cluster is one K3s server node, `legion`:

- `ansible/inventory/hosts.yaml` has one group, `k3s_servers`, with one host, `legion`. There is no `k3s_agents` group.
- `ansible/site.yaml` runs only against `k3s_servers`. It applies the roles `common`, `tailscale`, `nvidia`, `k3s_server`, and `argocd`. There is no agent role.
- The `k3s_server` role runs the K3s installer with `sh -s - server`. It does not read a join token or a server URL.
- The node uses its Tailscale IP as `node-ip` and `node-external-ip` (`k3s_node_ip` and `k3s_external_ip` in the inventory).
- `ansible/roles/k3s_server/templates/config.yaml.j2` hardcodes the node labels `gpu.nvidia.com/present=true` and `node.homelab/role=controlplane`. The `nvidia` role fails on a host where `nvidia-smi` does not run.

## What a worker join needs

To add a worker, add these items to the repo first:

- Step 1: An inventory group for agents, for example `k3s_agents` under `k3s_cluster`, with `ansible_host`, `ansible_user`, and `k3s_node_ip` set to the Tailscale IP of the worker.
- Step 2: An agent role that installs K3s in agent mode. It must pass the server URL (`https://<legion Tailscale IP>:6443`) and the node token from `/var/lib/rancher/k3s/server/node-token` on `legion`. Keep the token in Vault, not in Git.
- Step 3: A play in `ansible/site.yaml` that runs `common`, `tailscale`, and the agent role against the new group. Run `nvidia` only on hosts that have an NVIDIA GPU.
- Step 4: Node labels that come from inventory variables, not the hardcoded list in `config.yaml.j2`. Then only GPU nodes get `gpu.nvidia.com/present=true`.

Preview every Ansible change with `--check --diff` before you apply it.

## Check a node after a join

After you add the automation and join a worker, make sure that the node reports `Ready`:

```bash
kubectl get nodes -o wide
```

K3s runs Flannel inside the `k3s` process, so there is no Flannel pod to check. Make sure that workload pods are scheduled on the worker:

```bash
kubectl get pods -A -o wide
```

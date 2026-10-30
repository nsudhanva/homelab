---
title: Add Worker Node to K3s Cluster
description: How to approach adding a worker node to this K3s homelab. The cluster has one server node, and the repo does not automate worker joins yet.
keywords:
  - add k3s worker node
  - k3s cluster scaling
  - bare metal worker node
  - ansible k3s agent
  - kubernetes node expansion
sidebar:
  order: 2
---

# Add a Worker Node

:::caution

Joining workers is not automated in this repository yet. There is no `k3s_agents` inventory group and no agent role. If you run `ansible/site.yaml` with `--limit` on a new host, nothing joins the cluster. The playbook only targets `k3s_servers`.

:::

## Current state

- The cluster has one server node, `legion`, in the `k3s_servers` group of `ansible/inventory/hosts.yaml`.
- The `k3s_server` role installs K3s in server mode. It sets `node-ip` and `node-external-ip` to the Tailscale IP of the node (`k3s_node_ip` and `k3s_external_ip`). The LAN address can come from DHCP, because K3s does not use it.
- `ansible/roles/k3s_server/templates/config.yaml.j2` hardcodes the node labels `gpu.nvidia.com/present=true` and `node.homelab/role=controlplane`. There is no per-node label variable.
- The `nvidia` role fails on any host where `nvidia-smi` does not run.

## Step 1: Prepare the target machine

Install Ubuntu 26.04 LTS on the new machine. The LAN address can come from DHCP. Install Tailscale and run `sudo tailscale up`, as in [Host Preparation](/tutorials/system-prep/). Install your SSH public key and give the user passwordless sudo.

## Step 2: Add the agent automation

Add these items through Git before you join the node:

- An inventory group, for example `k3s_agents` under `k3s_cluster`. Set `ansible_host` and `k3s_node_ip` to the output of `tailscale ip -4` on the worker.
- An agent role that installs K3s in agent mode with the server URL `https://<legion Tailscale IP>:6443` and the node token. The token is in `/var/lib/rancher/k3s/server/node-token` on `legion`. Store it in Vault and read it at run time. Do not commit it.
- A play in `ansible/site.yaml` that runs `common`, `tailscale`, and the agent role against the new group. Run the `nvidia` role only on GPU hosts.
- A node label variable, so that only GPU nodes get `gpu.nvidia.com/present=true`.

## Step 3: Preview and run the playbook

Preview the change, then apply it:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml --limit <worker> --check --diff
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml --limit <worker>
```

## Step 4: Validate node registration

Make sure that the new node has joined and shows `Ready`:

```bash
kubectl get nodes -o wide
```

K3s runs Flannel inside the `k3s` process, so there is no Flannel pod to check. Make sure that pods can run on the new node:

```bash
kubectl get pods -A -o wide
```

---
title: Add Worker Node to K3s Cluster
description: Add a new bare-metal Ubuntu worker node to an existing K3s cluster. Covers the inventory, Ansible agent provisioning, GPU labels, and a check that the node joined the cluster.
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

Use this guide to add a bare-metal Ubuntu worker node to an existing K3s cluster.

## Step 1: Prepare the target machine

Install Ubuntu 26.04 LTS on the new machine. Configure a static LAN IP address. Make sure that the machine can connect to the control-plane node `legion`. Install your SSH public key for passwordless sudo access.

## Step 2: Retrieve the cluster node token

Log in to the control plane node `legion` and get the K3s node join token:

```bash
ssh sudhanva@100.66.139.118 "sudo cat /var/lib/rancher/k3s/server/node-token"
```

Keep this token in a secure location. You need it to register the agent.

## Step 3: Update the Ansible inventory

Add the new machine to `ansible/inventory/hosts.yaml` under the `k3s_agents` group:

```yaml
k3s_agents:
  hosts:
    worker-01:
      ansible_host: WORKER_TAILSCALE_IP
      ansible_user: sudhanva
      k3s_node_ip: "WORKER_TAILSCALE_IP"
```

Replace `WORKER_TAILSCALE_IP` with the output of `tailscale ip -4` on the worker. Each node uses its Tailscale IP as the node IP. Thus, the nodes connect to each other and to the API server over the tailnet, independently of the LAN addresses.

If the node has an NVIDIA GPU, add the node label `gpu.nvidia.com/present=true` under the node variables. The GPU Operator can then manage the node.

## Step 4: Provision the agent with Ansible

Run the Ansible playbook on the new worker node:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml --limit worker-01
```

Ansible installs the system prerequisites and configures the kernel modules and sysctl parameters. It then installs the K3s agent binary and registers the node with the control plane.

## Step 5: Validate node registration

From your workstation, make sure that the new node has joined and shows `Ready`:

```bash
kubectl get nodes -o wide
```

Make sure that the Flannel CNI pod runs on the new node:

```bash
kubectl get pods -n kube-system -o wide
```

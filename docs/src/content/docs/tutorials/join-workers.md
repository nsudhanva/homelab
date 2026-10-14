---
title: Add Worker Nodes to K3s Cluster
description: Add bare-metal Ubuntu worker nodes to an existing K3s cluster using Ansible automation.
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

When the control plane is operational, use this tutorial to add more worker nodes to your cluster.

## Step 1: Add the node to inventory

Add the new worker node to `ansible/inventory/hosts.yaml` under `k3s_agents`.

```yaml
k3s_agents:
  hosts:
    worker-01:
      ansible_host: WORKER_TAILSCALE_IP
      ansible_user: sudhanva
      k3s_node_ip: "WORKER_TAILSCALE_IP"
```

Replace `WORKER_TAILSCALE_IP` with the output of `tailscale ip -4` on the worker. Each node uses its Tailscale IP as the node IP. Thus the nodes connect to each other and to the API server over the tailnet, independent of the LAN addresses.

## Step 2: Run the agent provisioning role

Run Ansible on the target worker.

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml --limit worker-01
```

The playbook installs the prerequisites and joins the K3s cluster with the cluster join token. Then it starts the `k3s-agent` service.

## Step 3: Examine the new node

Make sure that the new worker reports `Ready` and shows its role.

```bash
kubectl get nodes -o wide
```

Make sure that the Flannel CNI pods and the workload pods are scheduled on the worker.

```bash
kubectl get pods -A -o wide
```

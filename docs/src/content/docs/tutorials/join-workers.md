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

Use this tutorial after the control plane is operational to scale out your cluster with additional worker nodes.

## Step 1: Add the node to inventory

Update `ansible/inventory/hosts.yaml` with the new worker node details under `k3s_agents`:

```yaml
k3s_agents:
  hosts:
    worker-01:
      ansible_host: 10.0.0.140
      ansible_user: sudhanva
      k3s_node_ip: "10.0.0.140"
```

## Step 2: Run the agent provisioning role

Execute Ansible against the target worker:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml --limit worker-01
```

The playbook installs prerequisites, joins the K3s cluster using the cluster join token, and starts the `k3s-agent` service.

## Step 3: Verify the new node

Confirm that the new worker reports `Ready` and displays its role:

```bash
kubectl get nodes -o wide
```

Check that the Flannel CNI and workload pods are scheduling onto the worker:

```bash
kubectl get pods -A -o wide
```

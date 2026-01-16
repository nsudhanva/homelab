---
title: Join Worker Nodes to Kubernetes Cluster
description: Generate a kubeadm join command and add Ubuntu worker nodes to an existing Kubernetes control plane for a multi-node bare-metal cluster.
keywords:
  - kubeadm join
  - kubernetes worker node
  - add node to cluster
  - kubeadm token
  - discovery-token-ca-cert-hash
  - multi-node kubernetes
  - kubernetes cluster expansion
sidebar:
  order: 8
---

# Join Worker Nodes

Use this after the control plane is initialized to add worker nodes to the cluster.
If you are adding a brand new node that has not been provisioned, start with [Add a Worker Node](../how-to/add-worker-node.md).

:::note

The Ansible provisioning playbook installs the required packages but does not run `kubeadm join`. Use this page after provisioning the worker.

:::

## Step 1: Generate a join command

Run this on the control plane:

```bash
kubeadm token create --print-join-command
```

:::note

The join command includes a short-lived token. Do not commit it to git or share it in public logs.

:::

## Step 2: Join each worker

Run the generated command on each worker node:

```bash
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

## Step 3: Verify the nodes

```bash
kubectl get nodes
```

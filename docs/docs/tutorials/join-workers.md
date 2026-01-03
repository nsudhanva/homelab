---
sidebar_position: 8
title: Join Worker Nodes
description: Join Ubuntu worker nodes to an existing kubeadm control plane for a bare-metal Kubernetes cluster.
keywords:
  - kubeadm join
  - add worker node
  - bare metal kubernetes
  - ubuntu 24.04
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

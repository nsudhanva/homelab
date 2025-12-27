---
sidebar_position: 8
title: Join Worker Nodes
---

# Join Worker Nodes

Use this after the control plane is initialized to add worker nodes to the cluster.

## Step 1: Generate a join command

Run this on the control plane:

```bash
kubeadm token create --print-join-command
```

## Step 2: Join each worker

Run the generated command on each worker node:

```bash
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

## Step 3: Verify the nodes

```bash
kubectl get nodes
```

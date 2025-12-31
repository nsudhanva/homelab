---
sidebar_position: 12
title: Add a Worker Node
description: Provision and join a new worker node to a bare-metal Kubernetes cluster managed with Ansible and kubeadm.
keywords:
  - add worker node
  - kubeadm join
  - ansible provisioning
  - bare metal kubernetes
  - ubuntu 24.04
---

# Add a Worker Node

Use this guide when you want to add a worker to an existing control plane without rebuilding the cluster.

## Step 1: Update the Ansible inventory

Add the new host under `k8s_workers` in `ansible/inventory/hosts.yaml`. If it is a CPU-only worker, also add it under `cpu_only`. If it is a GPU worker, add it under `gpu_nvidia` or `gpu_intel`.

## Step 2: Confirm node provisioning settings

Check the shared versions and paths in `ansible/group_vars/all.yaml`, especially:

Step 1: `k8s_version` for the apt repo
Step 2: `containerd_version` and `containerd_install_method`
Step 3: `longhorn_storage_path`

If you change `longhorn_storage_path`, also update the Longhorn bootstrap template in `bootstrap/templates/longhorn.yaml`.

## Step 3: Provision the worker with Ansible

Run the provisioning playbook from the repo root so paths resolve:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml \
  --limit <worker-hostname>
```

For GPU nodes, use the matching playbook:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-nvidia-gpu.yaml \
  -e @ansible/group_vars/all.yaml \
  --limit <worker-hostname>
```

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-intel-gpu.yaml \
  -e @ansible/group_vars/all.yaml \
  --limit <worker-hostname>
```

The playbook handles system prep, containerd, Kubernetes packages, Longhorn prerequisites, and the Tailscale client install.

## Step 4: (Optional) Enroll the node in Tailscale

The Ansible role installs `tailscaled` but does not join the tailnet. If you want tailnet SSH or access to the node, run:

```bash
sudo tailscale up
```

## Step 5: (Optional) Enable Longhorn disk creation on the node

If Longhorn is in use, label the node so it gets a default disk:

```bash
kubectl label node <worker-node-name> node.longhorn.io/create-default-disk=true --overwrite
```

## Step 6: Join the worker to the cluster

On the control plane, create a join command:

```bash
kubeadm token create --print-join-command
```

Run the generated command on the worker:

```bash
sudo kubeadm join <control-plane-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

## Step 7: Validate the node

```bash
kubectl get nodes
```

If the node stays `NotReady`, verify Cilium is installed and running on the control plane and that the worker can reach the API server.

---
title: From Scratch
description: Step-by-step guide to create a bare-metal Kubernetes cluster with kubeadm, Ansible, Cilium, and ArgoCD.
keywords:
  - bare metal kubernetes
  - how to create bare metal k8s
  - kubeadm
  - ansible provisioning
  - argocd gitops
  - cilium cni
---

# From Scratch

Use this guide to rebuild a homelab cluster from bare metal or new VM images using this repo as the source of truth.

## Step 1: Prepare the workstation

Follow [Prerequisites](../tutorials/prerequisites.md) to install tooling and update the Ansible inventory.

## Step 2: Provision nodes with Ansible

Run the provisioning playbook from the repo root:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml
```

If you need GPU support, use the GPU playbooks in `ansible/playbooks/`.

## Step 3: Initialize the control plane

Run on the control plane node:

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

If you want OIDC for Headlamp, follow the optional OIDC section in [Kubernetes](../tutorials/kubernetes.md) before the first `kubeadm init`.

## Step 4: Install Cilium

Update the control plane IP in `infrastructure/cilium/values.cilium`, then install Cilium:

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'"' '{print $2}')
cilium install --version $CILIUM_VERSION --values infrastructure/cilium/values.cilium
```

## Step 5: Install ArgoCD and bootstrap GitOps

```bash
kubectl apply -k bootstrap/argocd
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl apply -f bootstrap/root.yaml
```

## Step 6: Configure Vault and External Secrets

Follow [Vault](../how-to/vault.md) to initialize Vault and create the required secrets for ExternalDNS, cert-manager, and the Tailscale operator.

## Step 7: Validate the cluster

```bash
kubectl get nodes
kubectl get pods -A
kubectl get apps -n argocd
```

## Local rehearsal (Multipass)

Use this for a local dry run before touching hardware. To keep resources low, set a single-node cluster and smaller VM sizing. If resources are tight, disable Hubble UI and Relay for the rehearsal:

```bash
WORKER_COUNT=0 VM_CPUS=2 VM_MEMORY=3G VM_DISK=12G CILIUM_HUBBLE_ENABLED=false ./scripts/local-cluster.sh up
```

Destroy the rehearsal cluster when done:

```bash
./scripts/local-cluster.sh down
```

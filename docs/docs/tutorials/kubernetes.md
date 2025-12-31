---
sidebar_position: 4
title: Kubernetes
description: Install kubeadm, kubelet, and kubectl, then initialize a bare-metal Kubernetes control plane.
keywords:
  - kubeadm init
  - kubelet kubectl
  - bare metal kubernetes
  - ubuntu 24.04
  - control plane setup
---

# Kubernetes

:::note

If you ran the Ansible provisioning playbook, skip Step 1 and start at Step 2. The playbook installs and pins kubeadm/kubelet/kubectl but does not run `kubeadm init` or `kubeadm join`.

:::

## Step 1: Install Kubernetes packages

```bash
K8S_VERSION=$(grep -E "k8s_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'\"' '{print $2}')

sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/ /" | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

## Step 2: Initialize the control plane

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

:::note

If you maintain a kubeadm config, create `clusters/home/` and replace the command with `sudo kubeadm init --config clusters/home/kubeadm-clusterconfiguration.yaml`.

:::

## Optional: Enable Vault OIDC for Headlamp

If you want OIDC logins for Headlamp, add OIDC flags to the kubeadm config before the first `kubeadm init`. This avoids editing static manifests later.

Create `clusters/home/kubeadm-clusterconfiguration.yaml` with OIDC settings:

```yaml
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
apiServer:
  extraArgs:
    oidc-issuer-url: https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp
    oidc-client-id: REPLACE_WITH_VAULT_CLIENT_ID
    oidc-username-claim: sub
    oidc-groups-claim: groups
    oidc-username-prefix: "oidc:"
    oidc-groups-prefix: "oidc:"
```

Then initialize with:

```bash
sudo kubeadm init --config clusters/home/kubeadm-clusterconfiguration.yaml
```

If the cluster already exists, apply the same flags in `/etc/kubernetes/manifests/kube-apiserver.yaml` and let kubelet restart the API server.

## Step 3: Join worker nodes

Follow [Join Worker Nodes](./join-workers.md) after the control plane is ready.

## Step 4: Save kubeadm configuration

```bash
mkdir -p clusters/home
kubectl -n kube-system get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' > clusters/home/kubeadm-clusterconfiguration.yaml
```

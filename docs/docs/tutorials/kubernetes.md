---
sidebar_position: 4
title: Kubernetes
---

# Kubernetes

## Step: Install Kubernetes packages

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

:::note

Ansible installs and pins these packages for you when using the provisioning playbook.

:::

## Step: Initialize the control plane

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

:::note

If you maintain a kubeadm config in `clusters/home/kubeadm-clusterconfiguration.yaml`, you can replace the command with `sudo kubeadm init --config clusters/home/kubeadm-clusterconfiguration.yaml`.

:::

## Step: Save kubeadm configuration

```bash
kubectl -n kube-system get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' > clusters/home/kubeadm-clusterconfiguration.yaml
```

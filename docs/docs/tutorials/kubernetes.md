---
sidebar_position: 5
---

# Kubernetes

## Phase 3: Install Kubernetes

```bash
K8S_VERSION="v1.34.3"

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

## Phase 4: Initialize Cluster

```bash
sudo kubeadm init --skip-phases=addon/kube-proxy
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

> [!NOTE]
> During `kubeadm init`, kubeadm uploads the `ClusterConfiguration` to the `kubeadm-config` ConfigMap in `kube-system`. This repo captures that configuration in `clusters/home/kubeadm-clusterconfiguration.yaml`.

### Regenerate kubeadm cluster configuration

```bash
kubectl -n kube-system get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' > clusters/home/kubeadm-clusterconfiguration.yaml
```

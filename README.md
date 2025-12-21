# Homelab

Bare-metal Kubernetes cluster on Ubuntu 24.04, managed via GitOps with ArgoCD.

## Phase 0: Prerequisites

```bash
sudo apt update
sudo add-apt-repository ppa:quentiumyt/nvtop
sudo apt install -y curl wget git pre-commit python3 python3-dev htop nvtop
```

## Phase 1: System Preparation

```bash
# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Load kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# Configure sysctl
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system
```

## Phase 2: Install Containerd

```bash
sudo apt-get update
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl restart containerd
```

## Phase 3: Install Kubernetes

```bash
K8S_VERSION="v1.34"

sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list

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

# Allow scheduling on control plane (single-node)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

## Phase 5: Install Cilium

```bash
CILIUM_VERSION="1.18.5"
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)

curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}

cilium install --version $CILIUM_VERSION --set kubeProxyReplacement=true
cilium hubble enable --ui

# Verify
kubectl get nodes
cilium status
```

## Phase 6: Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
```

## Phase 7: GitOps Activation (Monorepo)

We use **ApplicationSets** to automatically manage applications and infrastructure.

1.  **Update Repo URL**: Edit `bootstrap/root.yaml` and replace `your-github-user` with your username.
2.  **Apply Bootstrap**:
    ```bash
    kubectl apply -f bootstrap/root.yaml
    ```
3.  **Done!**: ArgoCD will automatically discover and deploy everything in `infrastructure/` and `apps/`.

## Phase 8: Tailscale (Optional)

```bash
# Install Tailscale client
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Create OAuth secret (get credentials from https://login.tailscale.com/admin/settings/oauth)
kubectl create namespace tailscale
kubectl create secret generic operator-oauth \
  --namespace tailscale \
  --from-literal=client_id=YOUR_CLIENT_ID \
  --from-literal=client_secret=YOUR_CLIENT_SECRET

# ArgoCD will deploy the operator from manifests/tailscale-operator.yaml
```

## Quick Reference

```bash
# Cluster health
kubectl get nodes
kubectl get pods -A
cilium status

# ArgoCD UI
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Hubble UI
cilium hubble ui

# Force sync
kubectl -n argocd patch app root -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}' --type merge
```

## Expose Service via Tailscale

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
  annotations:
    tailscale.com/hostname: "my-app"
spec:
  type: LoadBalancer
  loadBalancerClass: tailscale
```

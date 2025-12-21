# Homelab

Bare-metal Kubernetes cluster on Ubuntu 24.04, managed via GitOps with ArgoCD.

## Phase 0: Prerequisites

```bash
sudo apt update
sudo add-apt-repository ppa:quentiumyt/nvtop
sudo apt install -y curl wget git pre-commit python3 python3-dev htop nvtop dmsetup
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install -y helm
```

---

## Phase 1: System Preparation

### Disable Swap (Permanently)

> [!IMPORTANT]
> Kubernetes requires swap to be disabled. If swap re-enables after reboot, kubelet will fail to start.

```bash
sudo swapoff -a
sudo sed -i '/\sswap\s/ s/^/#/' /etc/fstab
cat /etc/fstab | grep swap
free -h
```

### Load Kernel Modules

```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

### Configure Sysctl

```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

### Increase Inotify Limits

> [!NOTE]
> Many containers (Jellyfin, Longhorn, etc.) require higher inotify limits. Without this, containers crash with "too many open files" errors.

```bash
sudo sysctl -w fs.inotify.max_user_instances=512
sudo sysctl -w fs.inotify.max_user_watches=524288
echo "fs.inotify.max_user_instances=512" | sudo tee /etc/sysctl.d/99-inotify.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.d/99-inotify.conf
```

---

## Phase 2: Install Containerd

```bash
sudo apt-get update
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```

---

## Phase 3: Install Kubernetes

```bash
K8S_VERSION="v1.34"

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

---

## Phase 4: Initialize Cluster

```bash
sudo kubeadm init --skip-phases=addon/kube-proxy
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

---

## Phase 5: Install Cilium

```bash
CILIUM_VERSION="1.18.5"
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}
cilium install --version $CILIUM_VERSION --set kubeProxyReplacement=true
cilium hubble enable --ui
kubectl get nodes
cilium status
```

---

## Phase 6: Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

---

## Phase 7: Tailscale Setup

### Install Tailscale Client

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### Create OAuth Secret

Get OAuth credentials from https://login.tailscale.com/admin/settings/oauth (create with `devices:write` scope and tag `tag:k8s`).

```bash
kubectl create namespace tailscale
kubectl create secret generic operator-oauth \
  --namespace tailscale \
  --from-literal=client_id=YOUR_CLIENT_ID \
  --from-literal=client_secret=YOUR_CLIENT_SECRET
```

---

## Phase 8: Storage Prerequisites (Longhorn)

### Install Required Packages

```bash
sudo apt-get update
sudo apt-get install -y open-iscsi nfs-common cryptsetup
sudo systemctl enable --now iscsid
```

### Create Storage Directory

> [!IMPORTANT]
> Longhorn needs a storage directory to exist. Create it on your preferred disk.

```bash
mkdir -p /home/sudhanva/longhorn-storage
```

### Add Node Label for Longhorn Disk

> [!NOTE]
> With `createDefaultDiskLabeledNodes: true`, Longhorn only creates disks on nodes with this label.

```bash
kubectl label node $(hostname) node.longhorn.io/create-default-disk=true --overwrite
```

---

## Phase 9: GPU Support

### Intel GPU (iGPU for transcoding)

No host prerequisites needed - the Intel GPU Plugin DaemonSet handles everything.

Verify after deployment:
```bash
kubectl describe node | grep gpu.intel.com/i915
```

### NVIDIA GPU

#### Install NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg --yes
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

#### Configure Containerd for NVIDIA

> [!IMPORTANT]
> These three commands are ALL required for NVIDIA to work in Kubernetes:

```bash
sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default --cdi.enabled
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo systemctl restart containerd
```

Verify after deployment:
```bash
kubectl describe node | grep nvidia.com/gpu
```

---

## Phase 10: GitOps Activation

### Update Repository URLs

Edit these files and replace `YOUR_USERNAME` with your GitHub username:
- `bootstrap/root.yaml`
- `bootstrap/templates/infra-appset.yaml`
- `bootstrap/templates/apps-appset.yaml`

### Apply Bootstrap

```bash
kubectl apply -f bootstrap/root.yaml
```

### Apply Longhorn (special handling)

> [!NOTE]
> Longhorn is deployed as a separate ArgoCD Application because it uses Helm and needs to be in the `argocd` namespace.

```bash
kubectl apply -f bootstrap/longhorn.yaml
```

### Verify Deployment

```bash
kubectl get apps -n argocd
```

---

## Adding Nodes to the Cluster

This section covers expanding the cluster with additional worker nodes or control plane nodes.

### Prerequisites for New Nodes

Run these on each new node before joining:

```bash
sudo swapoff -a
sudo sed -i '/\sswap\s/ s/^/#/' /etc/fstab
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system
sudo sysctl -w fs.inotify.max_user_instances=512
sudo sysctl -w fs.inotify.max_user_watches=524288
echo "fs.inotify.max_user_instances=512" | sudo tee /etc/sysctl.d/99-inotify.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.d/99-inotify.conf
sudo apt-get update
sudo apt-get install -y containerd open-iscsi nfs-common cryptsetup
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
sudo systemctl enable --now iscsid
K8S_VERSION="v1.34"
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### For Nodes with NVIDIA GPU

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg --yes
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default --cdi.enabled
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo systemctl restart containerd
```

### Generate Join Token (On Existing Control Plane)

Tokens expire after 24 hours. Run this on an existing control plane node to generate a new join command:

```bash
kubeadm token create --print-join-command
```

### Add a Worker Node

Run the join command from above on the new worker node:

```bash
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

### Add a Control Plane Node (HA Setup)

> [!IMPORTANT]
> For HA control planes, you need a load balancer in front of all control planes and must initialize the first control plane with `--control-plane-endpoint=<load-balancer-ip>:6443`.

Generate a certificate key on an existing control plane:

```bash
sudo kubeadm init phase upload-certs --upload-certs
```

Then join with the `--control-plane` flag:

```bash
sudo kubeadm join <load-balancer-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <certificate-key>
```

After joining, configure kubectl on the new control plane:

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Configure Longhorn Storage on New Nodes

Label the node to enable Longhorn storage:

```bash
kubectl label node <new-node-name> node.longhorn.io/create-default-disk=true
```

Create storage directory on the new node:

```bash
mkdir -p /home/sudhanva/longhorn-storage
```

> [!NOTE]
> Longhorn requires 3+ nodes for full replication (replica count of 3). With fewer nodes, reduce the default replica count in Longhorn settings.

### Verify Node Joined

```bash
kubectl get nodes
kubectl get pods -A -o wide | grep <new-node-name>
```

### Node Types Summary

| Node Type | Join Command | Use Case |
|-----------|--------------|----------|
| **Worker** | `kubeadm join ... --token ... --discovery-token-ca-cert-hash ...` | Run workloads only |
| **Control Plane** | `kubeadm join ... --control-plane --certificate-key ...` | Run control plane + etcd (HA) |

### Longhorn Replication Best Practices

| Nodes | Recommended Replica Count | Notes |
|-------|--------------------------|-------|
| 1 | 1 | Single node, no redundancy |
| 2 | 2 | Can survive 1 node failure |
| 3+ | 3 | Full HA, survives 2 node failures |

---

## Troubleshooting

### Problem: Kubelet fails to start after reboot

**Symptom**: `kubectl get nodes` shows NotReady or connection refused.

**Cause**: Swap was re-enabled on boot.

**Solution**:
```bash
# Check if swap is on
free -h

# Disable swap
sudo swapoff -a

# Permanently disable (check fstab for uncommented swap lines)
sudo sed -i '/\sswap\s/ s/^/#/' /etc/fstab

# Restart kubelet
sudo systemctl restart kubelet
```

---

### Problem: Longhorn volumes stuck in "faulted" state

**Symptom**: PVCs show Pending, volumes show `faulted` in Longhorn.

**Cause**: Node has no disk configured (`disks: {}` in Longhorn node spec).

**Solution**:
```bash
# 1. Ensure storage directory exists
mkdir -p /home/sudhanva/longhorn-storage

# 2. Add the label for automatic disk creation
kubectl label node $(hostname) node.longhorn.io/create-default-disk=true

# 3. Restart Longhorn manager to detect the disk
kubectl rollout restart daemonset longhorn-manager -n longhorn-system
```

---

### Problem: ArgoCD Helm chart stuck on pre-upgrade hook

**Symptom**: Longhorn Application shows `waiting for completion of hook`, Job shows `ServiceAccount not found`.

**Cause**: ArgoCD runs Helm pre-upgrade hooks before creating the ServiceAccount they depend on.

**Solution**: Disable the pre-upgrade checker in Longhorn Helm values:

```yaml
# bootstrap/longhorn.yaml
helm:
  values: |
    preUpgradeChecker:
      jobEnabled: false
```

---

### Problem: Namespace stuck in Terminating state

**Symptom**: `kubectl delete ns` hangs forever.

**Cause**: Resources with finalizers are blocking deletion.

**Solution**:
```bash
# Remove finalizers from the namespace
kubectl get ns longhorn-system -o json | \
  jq '.spec.finalizers = []' | \
  kubectl replace --raw "/api/v1/namespaces/longhorn-system/finalize" -f -

# If a specific resource (like a Job) has a finalizer:
kubectl patch job <job-name> -n <namespace> -p '{"metadata":{"finalizers":null}}' --type=merge
```

---

### Problem: NVIDIA device plugin shows "invalid device discovery strategy"

**Symptom**: NVIDIA plugin pod crashes with error about incompatible strategy.

**Cause**: Containerd not configured with NVIDIA as default runtime + CDI not enabled.

**Solution**:
```bash
# Must use ALL THREE flags
sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default --cdi.enabled
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo systemctl restart containerd

# Then restart the plugin
kubectl delete pod -n kube-system -l name=nvidia-device-plugin-ds
```

---

### Problem: Containers crash with "too many open files" / inotify error

**Symptom**: Jellyfin or other apps crash with inotify limit errors.

**Cause**: Default Linux inotify limits (128 instances) are too low.

**Solution**:
```bash
# Apply immediately
sudo sysctl -w fs.inotify.max_user_instances=512
sudo sysctl -w fs.inotify.max_user_watches=524288

# Persist
echo "fs.inotify.max_user_instances=512" | sudo tee /etc/sysctl.d/99-inotify.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.d/99-inotify.conf
```

---

## Quick Reference

```bash
# Cluster health
kubectl get nodes
kubectl get pods -A
cilium status

# ArgoCD UI (port-forward)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# ArgoCD password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo

# Force ArgoCD sync
kubectl -n argocd patch app bootstrap -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}' --type merge

# Hubble UI
cilium hubble ui

# Check GPU availability
kubectl describe node | grep -E 'gpu.intel.com|nvidia.com'

# Check Longhorn volumes
kubectl get volumes.longhorn.io -A

# Check Longhorn node disks
kubectl get nodes.longhorn.io -n longhorn-system -o yaml | grep -A 10 'disks:'
```

---

## Deployed Components

After GitOps activation, ArgoCD automatically deploys:

| Component | Version | Description |
|-----------|---------|-------------|
| **Longhorn** | v1.7.2 | Distributed block storage (310GB configured) |
| **Intel GPU Plugin** | v0.34.0 | Exposes `gpu.intel.com/i915` for iGPU transcoding |
| **NVIDIA Device Plugin** | v0.17.0 | Exposes `nvidia.com/gpu` for dGPU workloads |
| **Jellyfin** | latest | Media server with Intel GPU + Longhorn storage |
| **ArgoCD Ingress** | - | HTTPS access via Tailscale |

---

## Expose Services via Tailscale (HTTPS)

Use a Kubernetes Ingress with `ingressClassName: tailscale` for automatic HTTPS/TLS.

### Example: Service + Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080
  selector:
    app: my-app
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  annotations:
    tailscale.com/tags: tag:k8s
    tailscale.com/https: "true"
spec:
  ingressClassName: tailscale
  tls:
    - hosts:
        - my-app
  rules:
    - host: my-app
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  number: 80
```

> [!IMPORTANT]
> The `tailscale.com/https: "true"` annotation ensures all traffic is served over HTTPS with automatic TLS certificates from Let's Encrypt.

Access at: `https://my-app.your-tailnet.ts.net`

---

## Repository Structure

```
homelab/
├── AGENTS.md               # AI assistant guidelines
├── README.md               # This file
├── bootstrap/
│   ├── root.yaml           # ArgoCD bootstrap Application
│   ├── longhorn.yaml       # Longhorn ArgoCD Application (Helm)
│   └── templates/
│       ├── infra-appset.yaml   # Infrastructure ApplicationSet
│       └── apps-appset.yaml    # Apps ApplicationSet
├── infrastructure/
│   ├── tailscale/          # Tailscale Operator
│   ├── gpu/
│   │   ├── intel-plugin.yaml   # Intel GPU DaemonSet
│   │   └── nvidia-plugin.yaml  # NVIDIA GPU DaemonSet
│   └── argocd-ingress/     # ArgoCD Tailscale Ingress
└── apps/
    ├── hello-homelab/      # Test application
    └── jellyfin/
        ├── pvc.yaml        # Persistent Volume Claims
        ├── deployment.yaml # Jellyfin Deployment
        ├── service.yaml    # ClusterIP Service
        └── ingress.yaml    # Tailscale Ingress
```

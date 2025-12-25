---
sidebar_position: 12
---

# Maintenance

## Adding Nodes to the Cluster

This section covers expanding the cluster with additional worker nodes or control plane nodes.

> [!NOTE]
> You can also add nodes by updating `ansible/inventory/hosts.yaml` and rerunning `ansible-playbook playbooks/site.yaml`.

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
K8S_VERSION="v1.34.3"
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

## Recreate From Scratch (Ubuntu 24.04)

Use this section when rebuilding a node from bare metal or VM images:

1. Install Ubuntu 24.04 LTS and log in as a user with sudo.
2. Clone this repo and review documentation for versions and paths.
3. Choose one path:
   - Automated: run Phase 0b (Ansible provisioning), then continue at Phase 4.
   - Manual: run Phases 0-11 in order.
4. Apply GitOps bootstrap (Phase 10) and verify (Phase 11).

If you are rebuilding with existing data disks for Longhorn, ensure the storage path in Phase 8 points to the correct mount before applying `bootstrap/templates/longhorn.yaml`.

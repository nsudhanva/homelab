# Homelab

Single-node bare-metal Kubernetes cluster on Ubuntu 24.04 LTS, managed via GitOps with ArgoCD.

## Documentation

All documentation lives under `docs/`. Use the Docusaurus site for tutorials, how-to guides, reference material, and explanations.

## Structure

- `ansible/`: Host provisioning roles and playbooks.
- `ansible/inventory/hosts.yaml`: Bare-metal inventory.
- `ansible/inventory/multipass.yaml`: Local VM inventory for Multipass clusters.
- `ansible/tests/local-cluster/test-nginx/deployment.yaml`: Local smoke test deployment.
- `ansible/tests/local-cluster/test-nginx/service.yaml`: Local smoke test service.
- `bootstrap/`: ArgoCD bootstrap + ApplicationSets.
- `clusters/`: Cluster-specific kubeadm config.
- `infrastructure/`: Cluster-wide components.
- `apps/`: User workloads.

## Quick Start (Bare Metal)

### Step: Provision the host

```bash
sudo apt-get update
sudo apt-get install -y openssh-server
```

### Step: Run Ansible provisioning

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e "target_hosts=k8s_nodes"
```

### Step: Install Kubernetes packages

```bash
K8S_VERSION="v1.35"

sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/${K8S_VERSION}/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/${K8S_VERSION}/deb/ /" | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### Step: Initialize the cluster

```bash
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --skip-phases=addon/kube-proxy

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

If you maintain a kubeadm config at `clusters/home/kubeadm-clusterconfiguration.yaml`, replace the command with `sudo kubeadm init --config clusters/home/kubeadm-clusterconfiguration.yaml --skip-phases=addon/kube-proxy`.

### Step: Install Cilium

```bash
CILIUM_VERSION="1.18.5"
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)

curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}

cilium install --version ${CILIUM_VERSION} --set kubeProxyReplacement=true
cilium hubble enable --ui
cilium status
```

### Step: Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

### Step: Bootstrap GitOps

```bash
kubectl apply -f bootstrap/root.yaml
```

## Local Multipass Cluster

See `docs/docs/tutorials/local-multipass-cluster.md` for the full Multipass-based walkthrough.

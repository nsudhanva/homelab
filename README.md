# Homelab

Bare-metal Kubernetes on Ubuntu 24.04 LTS with Ansible for node provisioning and ArgoCD for GitOps. The same repo supports local Multipass rehearsal and real hardware deployments.

## Documentation

Docs live in `docs/` and are built with Docusaurus.

```bash
cd docs
npm ci
npm run build
```

## Maintainers

- Sudhanva Narayana: https://sudhanva.me
- Maanasa Narayan: https://maanasanarayan.github.io

## Automation model

- **Ansible** provisions nodes (OS prep, containerd, kubeadm/kubelet/kubectl, storage prereqs).
- **ArgoCD** applies cluster state (infrastructure and apps) from Git.

## Structure

- `ansible/`: Host provisioning roles and playbooks.
- `ansible/inventory/hosts.yaml`: Bare-metal inventory.
- `ansible/inventory/multipass.yaml`: Local VM inventory for Multipass clusters.
- `ansible/tests/local-cluster/`: Smoke tests for a local cluster.
- `bootstrap/`: ArgoCD bootstrap and ApplicationSets.
- `clusters/`: Cluster-specific kubeadm config.
- `infrastructure/`: Cluster-wide components.
- `apps/`: User workloads.

## Quick Start (Bare Metal)

### Step 1: Prepare the inventory

Edit `ansible/inventory/hosts.yaml` with your control plane and worker IPs.

### Step 2: Run Ansible provisioning

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml
```

### Step 3: Initialize the control plane

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

If you maintain a kubeadm config at `clusters/home/kubeadm-clusterconfiguration.yaml`, replace the command with `sudo kubeadm init --config clusters/home/kubeadm-clusterconfiguration.yaml`.

### Step 4: Install Cilium

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'\"' '{print $2}')
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)

curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}

cilium install --version ${CILIUM_VERSION} --set kubeProxyReplacement=true
kubectl -n kube-system delete daemonset kube-proxy
cilium status
```

### Step 5: Install ArgoCD and bootstrap GitOps

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl apply -f bootstrap/root.yaml
```

### Step 6: Configure Gateway API custom domains (Tailscale + Cloudflare)

This repo uses Envoy Gateway with Tailscale as the LoadBalancer provider and ExternalDNS to manage subdomain records. Your apex `sudhanva.me` stays where it is; only subdomains that you annotate are managed here.

Step 1: Create Cloudflare API token secrets

```bash
kubectl create namespace external-dns
kubectl create secret generic cloudflare-api-token \
  --namespace external-dns \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN

kubectl create namespace cert-manager
kubectl create secret generic cloudflare-api-token \
  --namespace cert-manager \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN
```

Step 2: Update the ACME email

Set your email in `infrastructure/cert-manager-issuer/cluster-issuer.yaml`.

Step 3: Update the Tailscale Gateway target

Set `external-dns.alpha.kubernetes.io/target` in `infrastructure/gateway/gateway.yaml` to the Tailscale hostname created by Envoy Gateway (for example, `gateway-envoy.<tailnet>.ts.net`).

## Local Multipass Cluster

Use the Multipass walkthrough in `docs/docs/tutorials/local-multipass-cluster.md` to validate changes locally before moving to bare metal.

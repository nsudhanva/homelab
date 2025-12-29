# Homelab

Bare-metal Kubernetes on Ubuntu 24.04 LTS with Ansible for node provisioning and ArgoCD for GitOps.

## Quick Start

### Bare Metal (Primary)

```bash
# Edit inventory
nano ansible/inventory/hosts.yaml

# Provision nodes
ansible-playbook -i ansible/inventory/hosts.yaml ansible/playbooks/provision-cpu.yaml

# Initialize cluster (on control plane)
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
# Update k8sServiceHost in infrastructure/cilium/values.cilium to match the control plane IP
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'"' '{print $2}')
cilium install --version $CILIUM_VERSION --values infrastructure/cilium/values.cilium

# Install ArgoCD
kubectl apply -k bootstrap/argocd
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd

# Bootstrap GitOps
kubectl apply -f bootstrap/root.yaml
```

### Local Cluster (Optional Rehearsal)

```bash
./scripts/local-cluster.sh up
```

Creates a 3-node cluster on your workstation in ~10 minutes.

---

Bare metal is the primary target for this repo. Use the Multipass flow only to test changes before touching hardware.

## Documentation

Full docs at [docs.sudhanva.me](https://docs.sudhanva.me) or build locally:

```bash
cd docs && npm ci && npm start
```

## Structure

```
├── ansible/          # Node provisioning
├── bootstrap/        # ArgoCD bootstrap
├── infrastructure/   # Cluster components
├── apps/             # User workloads
├── scripts/          # Automation scripts
└── docs/             # Documentation (Docusaurus)
```

## Automation Model

- **Ansible** → Node configuration (OS, container runtime, kubelet)
- **ArgoCD** → Cluster state from Git (infrastructure, apps)

Push to Git. ArgoCD syncs automatically.

## Maintainers

- [Sudhanva Narayana](https://sudhanva.me)
- [Maanasa Narayan](https://maanasanarayan.github.io)

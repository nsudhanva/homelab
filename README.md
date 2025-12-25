# Homelab

Single-node bare-metal Kubernetes cluster on Ubuntu 24.04 LTS, managed via GitOps with ArgoCD.

## Documentation

Full documentation is available in the [docs](./docs) directory or at `https://docs.homelab` (internal).

To preview the docs locally:

```bash
cd docs
npm install
npm start
```

## Quick Start (from scratch)

1. **Provision Host**: Check `ansible/` for roles.
2. **Bootstrap Cluster**: Follow instructions in [docs/docs/kubernetes.md](docs/docs/kubernetes.md).
3. **Install Cilium**: [docs/docs/cilium.md](docs/docs/cilium.md).
4. **Install ArgoCD**: [docs/docs/argocd.md](docs/docs/argocd.md).
5. **Bootstrap GitOps**: Apply `bootstrap/root.yaml`.

## Structure

- `ansible/`: Host provisioning.
- `apps/`: User workloads (including these docs in `apps/docs`).
- `bootstrap/`: ArgoCD bootstrap.
- `clusters/`: Kubeadm config.
- `docs/`: Docusaurus source.
- `infrastructure/`: System components (Longhorn, GPU, etc.).

# AGENTS.md

Instructions for AI coding assistants working on this repository.

## Project Overview

Multi-node bare-metal Kubernetes cluster on Ubuntu 26.04 LTS using K3s, managed via GitOps with ArgoCD.

## Dos

- Always search online for latest stable versions before adding dependencies
- Always use Vault to store sensitive information or secrets
- Use ArgoCD ApplicationSets for deploying infrastructure and apps
- Place infrastructure components in `infrastructure/{component-name}/`
- Place user applications in `apps/{app-name}/`
- Use Tailscale Gateway API (`gatewayClassName: tailscale`) for HTTPS exposure
- Commit small, logical changes with descriptive messages. Use brief commit messages.
- If you add a new httproute, update homer configmap to add it to the dashboard
- Add any required documentation under `docs/`
- Use the [Divio documentation system](https://docs.divio.com/documentation-system/) for structuring docs:
  - **Tutorials**: Learning-oriented (e.g., "Setting up the cluster").
  - **How-To Guides**: Problem-oriented (e.g., "How to add a worker node").
  - **Reference**: Information-oriented (e.g., "Version matrix").
  - **Explanation**: Understanding-oriented (e.g., "GitOps Workflow explanation").

## Don'ts

- Do not add inline comments to YAML files
- Do not make unapproved changes as this repository is directly connected to the cluster
- Do not use numeric bullet points in any documentation .md files. Use something like "Step 1", "Step 2", etc. instead. Use headers or Astro Starlight provided syntax features
- Do not use `helm install` manually; let ArgoCD handle Helm charts
- Do not hardcode versions without researching the latest stable release
- Do not modify `/etc/fstab` or system files without explicit user approval
- Do not delete PVCs or any data volumes without explicit user approval
- Do not combine multiple resources in one YAML file; use separate files (deployment.yaml, service.yaml, ingress.yaml, pvc.yaml)

## Repository Structure

```bash
homelab/
├── bootstrap/               # ArgoCD bootstrap
│   ├── templates/           # ApplicationSet definitions
│   └── root.yaml            # Entrypoint
├── infrastructure/          # Cluster components (storage, networking, etc.)
├── apps/                    # User workloads
├── ansible/                # Ansible automation playbooks, roles, and inventory
├── scripts/                # Setup scripts (referenced by README)
└── README.md                # Single source of truth for setup
```

## Testing

Before pushing changes:

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
```

## Common Patterns

### Adding a New App

- Step 1: Create `apps/{app-name}/` directory
- Step 2: Add Kubernetes manifests (Deployment, Service, HTTPRoute, PVC, app.yaml, kustomization.yaml)
- Step 3: Push to Git; ArgoCD auto-deploys via ApplicationSet

### Adding Infrastructure

- Step 1: Create `infrastructure/{component}/` directory
- Step 2: For Helm charts: add `Chart.yaml` + `values.yaml`
- Step 3: For raw manifests: add YAML files directly
- Step 4: Push to Git; ArgoCD auto-deploys via ApplicationSet

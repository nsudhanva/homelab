# AGENTS.md

Instructions for AI coding assistants working on this repository.

## Project Overview

Single-node bare-metal Kubernetes cluster on Ubuntu 24.04 LTS, managed via GitOps with ArgoCD.

## Dos

- Always search online for latest stable versions before adding dependencies
- Follow the step-by-step format in README.md for any new setup instructions
- Use ArgoCD ApplicationSets for deploying infrastructure and apps
- Place infrastructure components in `infrastructure/{component-name}/`
- Place user applications in `apps/{app-name}/`
- Use Tailscale Ingress (`ingressClassName: tailscale`) for HTTPS exposure
- Commit small, logical changes with descriptive messages. Use brief commit messages.
- Add any required documentation under `docs/`
- Use the [Divio documentation system](https://docs.divio.com/documentation-system/) for structuring docs:
  - **Tutorials**: Learning-oriented (e.g., "Setting up the cluster").
  - **How-To Guides**: Problem-oriented (e.g., "How to add a worker node").
  - **Reference**: Information-oriented (e.g., "Version matrix").
  - **Explanation**: Understanding-oriented (e.g., "GitOps Workflow explanation").

## Don'ts

- Do not add inline comments to YAML files
- Do not use numeric bullet points in any documentation .md files. Use headers or docusaurus provided syntax features
- Do not use `helm install` manually; let ArgoCD handle Helm charts
- Do not hardcode versions without researching the latest stable release
- Do not modify `/etc/fstab` or system files without explicit user approval
- Do not combine multiple resources in one YAML file; use separate files (deployment.yaml, service.yaml, ingress.yaml, pvc.yaml)

## Repository Structure

```
homelab/
├── bootstrap/               # ArgoCD bootstrap
│   ├── templates/           # ApplicationSet definitions
│   └── root.yaml            # Entrypoint
├── infrastructure/          # Cluster components (storage, networking, etc.)
├── apps/                    # User workloads
├── clusters/                # Cluster-specific overrides (if needed)
├── manifests/               # Legacy (do not add new files here)
├── scripts/                 # Setup scripts (referenced by README)
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

1. Create `apps/{app-name}/` directory
2. Add Kubernetes manifests (Deployment, Service, Ingress, PVC)
3. Push to Git; ArgoCD auto-deploys via ApplicationSet

### Adding Infrastructure

1. Create `infrastructure/{component}/` directory
2. For Helm charts: add `Chart.yaml` + `values.yaml`
3. For raw manifests: add YAML files directly
4. Push to Git; ArgoCD auto-deploys via ApplicationSet

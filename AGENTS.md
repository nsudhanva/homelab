# AGENTS.md

Instructions for AI coding assistants working on this repository.

## Project Overview

Multi-node bare-metal Kubernetes cluster on Ubuntu 26.04 LTS using K3s, managed via GitOps with ArgoCD.

## Dos

- Always search online for latest stable versions before adding dependencies
- Always use Vault to store sensitive information or secrets. Every Kubernetes Secret must come from an `ExternalSecret` that reads a Vault path; write the value to Vault first, then reference it
- Make every cluster change through Git and let ArgoCD apply it. Imperative `kubectl` is limited to read-only inspection, logs, and triggering a Job from an existing CronJob
- Make every node-level change (K3s config, systemd units, Tailscale settings, sysctls) through the Ansible roles in `ansible/`, previewed with `--check --diff`
- Set explicit CPU and memory requests and limits on every Deployment, Job, and CronJob, keeping total requests within node allocatable
- Declare fields you rely on explicitly (for example `suspend: false` on CronJobs) so ArgoCD detects and reverts drift
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
- For all Python projects and microservices in `apps/`: use `uv` for package and virtual environment management, `ruff` for linting and formatting, and `ty` for static type checking. Always include `ruff` and `ty` in the project's dev dependencies (`pyproject.toml`) and ensure `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check` pass cleanly before committing.

## Don'ts

- Do not add inline comments to YAML files
- Do not make unapproved changes as this repository is directly connected to the cluster
- Do not use numeric bullet points in any documentation .md files. Use something like "Step 1", "Step 2", etc. instead. Use headers or Astro Starlight provided syntax features
- Do not use `helm install` manually; let ArgoCD handle Helm charts
- Do not hardcode versions without researching the latest stable release
- Do not modify `/etc/fstab` or system files without explicit user approval
- Do not delete PVCs or any data volumes without explicit user approval
- Do not combine multiple resources in one YAML file; use separate files (deployment.yaml, service.yaml, ingress.yaml, pvc.yaml)
- Do not commit secrets, tokens, passwords, API keys, account numbers, or personal financial data. This is a public repository; `gitleaks` runs in pre-commit and CI
- Do not put credentials in scripts; scripts read them from Vault or environment variables at runtime
- Do not create, patch, or delete Secrets, CronJobs, Deployments, or ArgoCD Applications with `kubectl`; change the manifests in Git instead
- Do not change Tailscale DNS, node IPs, or node networking outside the `tailscale` and `k3s_server` Ansible roles. Nodes use their Tailscale IP as `node-ip` and run with Tailscale DNS disabled
- Do not run long batch workloads that exceed node allocatable; schedule them through CronJobs with resource limits

## Repository Structure

```bash
homelab/
├── bootstrap/               # ArgoCD bootstrap
│   ├── templates/           # ApplicationSet definitions
│   └── root.yaml            # Entrypoint
├── infrastructure/          # Cluster components (storage, networking, etc.)
├── apps/                    # User workloads
├── packages/                # Shared monorepo libraries (e.g. homelab-ai)
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
kubectl get applications -n argocd
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

### Adding a Python Application

- Step 1: Create `apps/{app-name}/` with standard package layout (`src/{package_name}`, `tests/`, `pyproject.toml`, `Dockerfile`)
- Step 2: Manage dependencies using `uv` with lockfile (`uv.lock`)
- Step 3: Include `ruff` and `ty` in the dev dependency group in `pyproject.toml`
- Step 4: Configure `[tool.ruff]` and `[tool.ty]` in `pyproject.toml`
- Step 5: Verify all linters and type checks pass: `uv run ruff check`, `uv run ruff format --check`, `uv run ty check`, and `uv run pytest`
- Step 6: Add Kubernetes manifests and push to Git for ArgoCD deployment

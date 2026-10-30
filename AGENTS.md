# AGENTS.md

Instructions for AI coding assistants that work on this repository.

## Project Overview

A multi-node bare-metal Kubernetes cluster on Ubuntu 26.04 LTS. It uses K3s. ArgoCD manages it through GitOps.

## Dos

- Always search online for the latest stable versions before you add dependencies
- Always use Vault to keep sensitive information or secrets. Every Kubernetes Secret must come from an `ExternalSecret` that reads a Vault path. Write the value to Vault first, then refer to it
- Make every cluster change through Git and let ArgoCD apply it. Use imperative `kubectl` only for read-only inspection, logs, and to start a Job from an existing CronJob
- Make every node-level change (K3s config, systemd units, Tailscale settings, sysctls) through the Ansible roles in `ansible/`. Preview each change with `--check --diff`
- Make every tailnet change (policy file, DNS, tailnet settings, device tags) in `terraform/tailscale/`. Review the plan from the `Tailscale` workflow, then apply it with a manual run of that workflow
- Set explicit CPU and memory requests and limits on every Deployment, Job, and CronJob. Keep the total requests within node allocatable
- Declare explicitly the fields that you depend on (for example `suspend: false` on CronJobs). Then ArgoCD can find and revert drift
- Use ArgoCD ApplicationSets to deploy infrastructure and apps
- Place infrastructure components in `infrastructure/{component-name}/`
- Place user applications in `apps/{app-name}/`
- Use Tailscale Gateway API (`gatewayClassName: tailscale`) for HTTPS exposure
- Commit small, logical changes with messages that describe them. Use short commit messages.
- If you add a new httproute, update the homer configmap to add it to the dashboard
- Add all necessary documentation under `docs/`
- Write docs and READMEs in ASD-STE100 Simplified Technical English, with the rules in `docs/src/content/docs/reference/docs-structure.md` (Writing Standard). Describe the current state only: no history of changes, no rejected options, and no marketing language or AI filler
- Use the [Divio documentation system](https://docs.divio.com/documentation-system/) to structure docs:
  - **Tutorials**: Learning-oriented (e.g., "Setting up the cluster").
  - **How-To Guides**: Problem-oriented (e.g., "How to add a worker node").
  - **Reference**: Information-oriented (e.g., "Version matrix").
  - **Explanation**: Understanding-oriented (e.g., "GitOps Workflow explanation").
- For all Python projects and microservices in `apps/`, use `uv` to manage packages and virtual environments. Use `ruff` for linting and formatting, and `ty` for static type checks. Always include `ruff` and `ty` in the dev dependencies of the project (`pyproject.toml`). Before you commit, make sure that `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check` pass with no errors.

## Don'ts

- Do not add inline comments to YAML files
- Do not make unapproved changes. This repository connects directly to the cluster
- Do not use numeric bullet points in any documentation .md files. Use "Step 1", "Step 2", and so on instead. Use headers or the syntax features that Astro Starlight gives
- Do not use `helm install` manually. Let ArgoCD manage Helm charts
- Do not hardcode versions before you research the latest stable release
- Do not modify `/etc/fstab` or system files without explicit user approval
- Do not delete PVCs or any data volumes without explicit user approval
- Do not put more than one resource in one YAML file. Use separate files (deployment.yaml, service.yaml, ingress.yaml, pvc.yaml)
- Do not commit secrets, tokens, passwords, API keys, account numbers, or personal financial data. This is a public repository. `gitleaks` runs in pre-commit and CI
- Do not put credentials in scripts. Scripts read them from Vault or environment variables at runtime
- Do not create, patch, or delete Secrets, CronJobs, Deployments, or ArgoCD Applications with `kubectl`. Change the manifests in Git instead
- Do not change Tailscale DNS, node IPs, or node networking outside the `tailscale` and `k3s_server` Ansible roles. Nodes use their Tailscale IP as `node-ip` and run with Tailscale DNS disabled
- Do not change the tailnet policy, DNS, settings, or device tags in the Tailscale admin console. Change `terraform/tailscale/` instead
- Do not commit Terraform state, plan files, or `.tfvars` files, and do not manage OAuth clients or auth keys in Terraform, because their secrets would be stored in state
- Do not run long batch workloads that need more than node allocatable. Schedule them through CronJobs with resource limits

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
├── terraform/               # Terraform for services outside the cluster (tailscale/)
├── scripts/                # Setup scripts (referenced by README)
└── README.md                # Single source of truth for setup
```

## Testing

Before you push changes, run these commands:

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
kubectl get applications -n argocd
```

## Common Patterns

### Adding a New App

- Step 1: Create the `apps/{app-name}/` directory
- Step 2: Add Kubernetes manifests (Deployment, Service, HTTPRoute, PVC, app.yaml, kustomization.yaml)
- Step 3: Push to Git. ArgoCD deploys the app automatically through the ApplicationSet

### Adding Infrastructure

- Step 1: Create the `infrastructure/{component}/` directory
- Step 2: For Helm charts, add an ArgoCD `Application` (for example `{component}.yaml`) with a Helm `source`. Put the values inline, or in a values file that the Application reads through a `$values` source
- Step 3: For upstream release manifests, add a `kustomization.yaml` that references the pinned release URLs, with `patches` for local changes. Do not vendor large upstream files
- Step 4: For raw manifests, add the YAML files directly, one resource per file
- Step 5: Push to Git. ArgoCD deploys the component automatically through the ApplicationSet

### Adding a Python Application

- Step 1: Create `apps/{app-name}/` with the standard package layout (`src/{package_name}`, `tests/`, `pyproject.toml`, `Dockerfile`)
- Step 2: Use `uv` with a lockfile (`uv.lock`) to manage dependencies
- Step 3: Include `ruff` and `ty` in the dev dependency group in `pyproject.toml`
- Step 4: Configure `[tool.ruff]` and `[tool.ty]` in `pyproject.toml`
- Step 5: Make sure that all linters and type checks pass: `uv run ruff check`, `uv run ruff format --check`, `uv run ty check`, and `uv run pytest`
- Step 6: Add the Kubernetes manifests and push to Git. ArgoCD then deploys the app

# ArgoCD Cluster Configuration

This directory represents the configuration for the `home` cluster.

## Structure

- **bootstrap/**: Contains the `ApplicationSet` definitions.
- **infrastructure/**: Contains core infrastructure components (e.g., Tailscale).
- **apps/**: Contains user applications.

## How it works

1.  **bootstrap/root.yaml:** The "Master App" that must be applied manually (`kubectl apply -f bootstrap/root.yaml`).
2.  **ApplicationSets:** The root app deploys the ApplicationSets found in `bootstrap/templates/`.
3.  **Auto-Discovery:** The ApplicationSets automatically create an ArgoCD Application for every subdirectory found in `infrastructure/` and `apps/`.

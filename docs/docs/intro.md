---
sidebar_position: 1
---

# Introduction

Single-node bare-metal Kubernetes cluster on Ubuntu 24.04 LTS, managed via GitOps with ArgoCD.

This repo is the source of truth for:
- Host provisioning (Ansible roles).
- Cluster bootstrap (kubeadm + Cilium + ArgoCD).
- Infrastructure and application manifests (ArgoCD ApplicationSets).

## Quick Map

- \`ansible/\`: host provisioning roles and playbooks.
- \`bootstrap/\`: ArgoCD bootstrap + ApplicationSets.
- \`infrastructure/\`: cluster-wide components.
- \`apps/\`: user workloads.
- \`clusters/home/\`: cluster-specific kubeadm config.

## Architecture

\`\`\`mermaid
graph TD
  Host[Ubuntu 24.04 Node] --> Kubeadm[Kubeadm Control Plane]
  Kubeadm --> Cilium[Cilium CNI]
  Kubeadm --> ArgoCD[ArgoCD]
  ArgoCD --> AppSets[ApplicationSets]
  AppSets --> Infra[infrastructure/*]
  AppSets --> Apps[apps/*]
  Infra --> Tailscale[Tailscale Operator]
  Infra --> Longhorn[Longhorn]
  Apps --> Jellyfin[Jellyfin]
  Apps --> Filebrowser[Filebrowser]
  Apps --> Hello[hello-homelab]
\`\`\`

\`\`\`mermaid
sequenceDiagram
  participant Git as Git Repo
  participant Argo as ArgoCD
  participant K8s as Kubernetes API
  Git->>Argo: Detect changes
  Argo->>K8s: Apply manifests
  K8s-->>Argo: Sync status
\`\`\`

## Versions (Pinned)

- Kubernetes: \`v1.34.3\` in \`ansible/group_vars/all.yaml\` and \`clusters/home/kubeadm-clusterconfiguration.yaml\`.
- Cilium: \`1.18.5\` in this README and \`ansible/group_vars/all.yaml\`.
- Longhorn: \`1.7.2\` in \`bootstrap/templates/longhorn.yaml\`.
- Tailscale Operator: \`1.78.3\` in \`infrastructure/tailscale/tailscale-operator.yaml\`.
- Intel GPU plugin: \`0.34.0\` in \`infrastructure/gpu/intel-plugin.yaml\`.
- NVIDIA GPU plugin: \`0.17.0\` in \`infrastructure/gpu/nvidia-plugin.yaml\`.

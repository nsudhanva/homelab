---
title: Automation Model
---

# Automation Model

This repository is designed for maximum automation. Every change should flow through one of two systems:

- **Ansible** for node and host configuration
- **ArgoCD** for cluster and application manifests

If a change does not fit into those two paths, treat it as an exception and document it.

```mermaid
flowchart TB
  subgraph Git["Git repository"]
    AnsibleRepo["ansible/"]
    InfraRepo["infrastructure/"]
    AppsRepo["apps/"]
  end

  subgraph Hosts["Ubuntu nodes"]
    OS["OS, containerd, kubelet"]
    Kubeadm["kubeadm init/join"]
  end

  subgraph Cluster["Kubernetes cluster"]
    Argo["ArgoCD"]
    AppSets["ApplicationSets"]
    Workloads["Apps + infrastructure"]
  end

  AnsibleRepo -->|"Ansible playbooks"| OS
  OS --> Kubeadm
  Kubeadm --> Argo
  InfraRepo --> AppSets
  AppsRepo --> AppSets
  Argo --> AppSets
  AppSets --> Workloads
```

## Detailed Automation Flow

```mermaid
flowchart LR
  subgraph Repo["homelab repo"]
    Inventory["ansible/inventory/hosts.yaml"]
    Vars["ansible/group_vars/all.yaml"]
    Playbooks["ansible/playbooks/*"]
    Roles["ansible/roles/*"]
    Bootstrap["bootstrap/root.yaml"]
    AppSetInfra["bootstrap/templates/infra-appset.yaml"]
    AppSetApps["bootstrap/templates/apps-appset.yaml"]
    InfraDir["infrastructure/*"]
    AppsDir["apps/*"]
  end

  subgraph Hosts["Bare metal nodes"]
    Base["Base OS config"]
    Containerd["containerd"]
    Kubelet["kubelet"]
  end

  subgraph ControlPlane["Control plane"]
    KubeadmInit["kubeadm init"]
    CiliumInstall["cilium install"]
    ArgoCD["ArgoCD"]
  end

  subgraph Cluster["Cluster objects"]
    AppSet1["ApplicationSet: infra"]
    AppSet2["ApplicationSet: apps"]
    InfraApps["infra-* Applications"]
    UserApps["app-* Applications"]
    HelmCharts["Helm chart releases"]
    RawManifests["Raw manifests"]
  end

  Inventory --> Playbooks
  Vars --> Playbooks
  Roles --> Playbooks
  Playbooks --> Base
  Base --> Containerd
  Base --> Kubelet
  Kubelet --> KubeadmInit
  KubeadmInit --> CiliumInstall
  CiliumInstall --> ArgoCD
  Bootstrap --> ArgoCD
  ArgoCD --> AppSet1
  ArgoCD --> AppSet2
  AppSetInfra --> InfraApps
  AppSetApps --> UserApps
  InfraDir --> InfraApps
  AppsDir --> UserApps
  InfraApps --> HelmCharts
  InfraApps --> RawManifests
  UserApps --> RawManifests
```

## What Ansible owns

Ansible is the source of truth for host provisioning and OS configuration:

- Kernel modules and sysctl
- Container runtime configuration
- Kubernetes package installation and pinning
- Storage prerequisites and node services

## What ArgoCD owns

ArgoCD is the source of truth for everything that runs inside the cluster:

- Infrastructure from `infrastructure/`
- Applications from `apps/`
- Helm-based components like Longhorn

## Automation guardrails

:::note

Avoid running `kubectl apply` against app or infrastructure directories. Push to Git and let ArgoCD reconcile.

:::

:::note

Avoid manual edits on nodes. Update Ansible inputs and re-run the playbooks.

:::

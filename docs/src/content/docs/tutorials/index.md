---
title: K3s Cluster Setup Tutorials
description: Step-by-step tutorials to build a bare-metal K3s Kubernetes cluster on Ubuntu 26.04 LTS with Ansible automation and ArgoCD GitOps.
keywords:
  - k3s tutorial
  - bare metal kubernetes setup
  - ubuntu 26.04 kubernetes
  - ansible automation k3s
  - argocd gitops setup
sidebar:
  order: 1
---

# Cluster Setup Tutorials

These tutorials show you, step by step, how to build a bare-metal K3s Kubernetes cluster from scratch. The cluster runs on node `legion` (Ubuntu 26.04 LTS).

```mermaid
flowchart TD
  Start["Start here"] --> Prereq["Step 1: Prerequisites"]
  Prereq --> Prep["Step 2: Host Preparation"]
  Prep --> Config["Step 3: Ansible Configuration"]
  Config --> Provision["Step 4: K3s Provisioning"]
  Provision --> Argo["Step 5: ArgoCD GitOps Bootstrap"]
  Argo --> Workers["Step 6: Expand Worker Nodes"]
```

## Tutorial Roadmap

Do these tutorials in sequence. The result is a homelab cluster that is reproducible and ready for production:

| Stage | Tutorial | Deliverable |
|---|---|---|
| Step 1 | [Prerequisites](./prerequisites.md) | Workstation dependencies and access credentials |
| Step 2 | [Host Preparation](./system-prep.md) | Ubuntu 26.04 installation, networking, and storage mount |
| Step 3 | [Ansible Configuration](./containerd.md) | Inventory variables and host role definitions |
| Step 4 | [K3s Bootstrap](./kubernetes.md) | Live K3s cluster with Flannel CNI and NVIDIA CDI |
| Step 5 | [ArgoCD and GitOps](./argocd.md) | Declarative infrastructure and app synchronization |
| Step 6 | [Add Workers](./join-workers.md) | Multi-node scaling with K3s agent nodes |
